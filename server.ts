import express from "express";
import { createServer as createViteServer } from "vite";
import { execFile } from "child_process";
import { promisify } from "util";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

const execFileAsync = promisify(execFile);
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const AGENT_ROOT = path.resolve(__dirname, "gemma4-agent");

async function listFilesRecursive(dir: string, baseDir: string = dir): Promise<string[]> {
  try {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    const files: string[] = [];
    for (const entry of entries) {
      if (entry.name === "__pycache__" || entry.name.startsWith(".")) continue;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        files.push(...(await listFilesRecursive(full, baseDir)));
      } else {
        files.push(path.relative(baseDir, full));
      }
    }
    return files.sort();
  } catch {
    return [];
  }
}

async function startServer() {
  const app = express();
  const PORT = 3000;
  app.use(express.json());

  // Warm up repository_knowledge cache by running E5
  try {
    await execFileAsync("python3", [path.join(AGENT_ROOT, "cli.py"), "--experiment", "E5"], {
      cwd: AGENT_ROOT,
      timeout: 30000,
    });
  } catch (err) {
    console.error("Initial warmup notice:", err);
  }

  app.get("/api/status", async (_req, res) => {
    try {
      const files = await listFilesRecursive(AGENT_ROOT);
      let configRaw = "";
      try {
        configRaw = await fs.readFile(
          path.join(AGENT_ROOT, "config", "experiment.yaml"),
          "utf-8"
        );
      } catch {
        configRaw = "# Default config";
      }

      res.json({
        service: "gemma4-swe-agent-backend",
        version: "0.1.0",
        model: "gemma-4-31b-it-qat-w4a16-ct",
        doctrine: "UNDERSTAND -> LOCALIZE -> PLAN -> PATCH -> VALIDATE -> LEARN",
        backend_status: "operational",
        agent_root: "gemma4-agent/",
        files_count: files.length,
        files,
        default_experiment_yaml: configRaw,
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/manifest", async (_req, res) => {
    try {
      const manifest = await fs.readFile(
        path.join(__dirname, "GEMMA4_AGENT_MANIFEST.md"),
        "utf-8"
      );
      res.type("text/plain").send(manifest);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/knowledge", async (_req, res) => {
    try {
      const kdir = path.join(AGENT_ROOT, "repository_knowledge");
      const artifactNames = [
        "repo_summary.md",
        "execution_flows.md",
        "functions.json",
        "classes.json",
        "modules.json",
        "tests.json",
        "call_graph.json",
        "flow_graph.json",
        "logger_state.json",
      ];
      const artifacts: Record<string, any> = {};
      for (const name of artifactNames) {
        try {
          const raw = await fs.readFile(path.join(kdir, name), "utf-8");
          artifacts[name] = name.endsWith(".json") ? JSON.parse(raw) : raw;
        } catch {
          artifacts[name] = null;
        }
      }
      res.json(artifacts);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get("/api/file", async (req, res) => {
    try {
      const rel = String(req.query.path || "config/experiment.yaml");
      const safePath = path.resolve(AGENT_ROOT, rel);
      if (!safePath.startsWith(AGENT_ROOT)) {
        res.status(400).json({ error: "Path must be inside gemma4-agent/" });
        return;
      }
      const content = await fs.readFile(safePath, "utf-8");
      res.json({ path: rel, content });
    } catch (err: any) {
      res.status(404).json({ error: err.message });
    }
  });

  app.post("/api/run", async (req, res) => {
    try {
      const experiment = String(req.body?.experiment || "E5");
      const demoFailureLoop = Boolean(req.body?.demoFailureLoop);
      const args = [path.join(AGENT_ROOT, "cli.py"), "--experiment", experiment];
      if (demoFailureLoop) {
        args.push("--demo-failure-loop");
      }
      const { stdout } = await execFileAsync("python3", args, {
        cwd: AGENT_ROOT,
        timeout: 30000,
      });
      res.json(JSON.parse(stdout));
    } catch (err: any) {
      res.status(500).json({ error: err.message, stderr: err.stderr });
    }
  });

  app.post("/api/matrix", async (_req, res) => {
    try {
      const { stdout } = await execFileAsync(
        "python3",
        [path.join(AGENT_ROOT, "cli.py"), "--matrix"],
        { cwd: AGENT_ROOT, timeout: 60000 }
      );
      res.json(JSON.parse(stdout));
    } catch (err: any) {
      res.status(500).json({ error: err.message, stderr: err.stderr });
    }
  });

  app.post("/api/test", async (_req, res) => {
    try {
      const { stdout, stderr } = await execFileAsync(
        "python3",
        [path.join(AGENT_ROOT, "tests", "test_pipeline.py"), "-v"],
        { cwd: AGENT_ROOT, timeout: 30000 }
      );
      res.json({
        passed: true,
        output: (stdout + "\n" + stderr).trim(),
      });
    } catch (err: any) {
      res.status(500).json({
        passed: false,
        output: ((err.stdout || "") + "\n" + (err.stderr || err.message)).trim(),
      });
    }
  });

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Gemma 4 SWE Agent Backend listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
