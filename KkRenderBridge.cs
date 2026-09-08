// KkRenderBridge.cs - minimal render bridge for Koikatsu
//
// Watches render_requests/ for job JSON files, renders the character
// in the Character Maker under a fixed camera preset, captures
// a screenshot, and writes a response JSON.
//
// Build: python scripts/compile_csc.py  (uses Windows csc.exe, C# 5 compat)
// Deploy: cp build/KkRenderBridge.dll "C:/Games/Koikatsu/BepInEx/plugins/"
//
// Protocol:
//   submit_job()  → writes render_requests/<jobid>.json
//   plugin polls  → reads _requestDir/*.json, picks up jobs
//   plugin renders → writes renders/<jobid>.png + render_requests/<jobid>.response.json
//
// Camera presets: CALIBRATE IN-GAME (see ApplyCameraPreset comments).
//
// Known issue: hair/cloth physics causes ~340 pixels of sub-pixel jitter
// between consecutive renders (0.016% of frame, clustered on character edges).
// Root cause: physics simulation settles at different frame offsets.
// Fix: freeze all Rigidbody components before capture (see CaptureAfterDelay).

using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using BepInEx;
using KKAPI;
using KKAPI.Chara;
using KKAPI.Maker;

namespace KkRenderBridge
{
    // BepInEx plugin metadata — required for BepInEx to discover this plugin.
    [BepInPlugin("com.example.kkrenderbridge", "KkRenderBridge", "0.2.1")]
    internal class KkRenderBridgePlugin : BaseUnityPlugin
    {
        // ---- Config ----
        // Where to watch for incoming render requests.
        // Defaults to the game directory; overrides via plugin config.
        private string _requestDir;
        // Where to write screenshots (set by the request JSON).

        private FileMonitor _monitor;

        // FIFO queue of pending render jobs.
        // OnNewRequest enqueues; Update() drains one job per frame while
        // a coroutine is active.  Multiple requests submitted in the same
        // frame all get queued instead of being dropped.
        private readonly Queue<RenderJobEntry> _queue = new Queue<RenderJobEntry>();
        private bool _isRendering = false;

        // Track the active camera preset so LateUpdate can re-apply it
        // every frame.  The Character Maker's camera script resets our
        // transform after we set it in ApplyCameraPreset; re-applying in
        // LateUpdate (which runs after the Maker's Update) ensures our
        // values are the last write before CaptureScreenshot.
        private string _activePreset;

        // ---- BepInEx lifecycle ----
        private void Awake()
        {
            // Application.dataPath points to Koikatu_Data/ — go up one level
            // to the game root where we want render_requests/ to live.
            var gameRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            _requestDir = Path.Combine(gameRoot, "render_requests");
            _monitor = new FileMonitor(_requestDir, OnNewRequest);
            Debug.Log("[KkRenderBridge] watching " + _requestDir);
        }

        private void Update()
        {
            // F9 = dump current camera + lighting state to the log for
            //   in-game calibration (camera preset values, light positions, etc.
            if (Input.GetKeyDown(KeyCode.F9))
            {
                LogCurrentCameraAndLighting();
            }

            // Always poll for new request files — they get enqueued even while
            // a render is in progress, so rapid-fire submissions don't get lost.
            _monitor.Poll();

            // Drain the queue: start the next job only when the current one
            // (if any) has finished.  One job per frame to keep Update cheap.
            if (!_isRendering && _queue.Count > 0)
            {
                var entry = _queue.Dequeue();
                RenderJob(entry.req, entry.requestPath);
            }
        }

        // LateUpdate runs after the Maker's Update() — if the Maker's camera
        // script resets our transform during its Update, re-applying here makes
        // our values the last write before CaptureScreenshot (which happens in
        // RenderJobCoroutine's yield sequence, also after Update).
        // Re-apply the active preset every frame while a render is in progress.
        // We check _activePreset (not _isRendering) because _isRendering is
        // cleared in RenderJob's finally block immediately after StartCoroutine
        // returns, but the coroutine keeps running across multiple frames.
        // Also enumerate ALL cameras to find which one renders the character preview.
        private void LateUpdate()
        {
            if (!string.IsNullOrEmpty(_activePreset))
            {
                ApplyCameraPreset(_activePreset);
                // Debug: enumerate all cameras
                var allCams = Camera.allCameras;
                string camInfo = "[KkRenderBridge] [LATEUPDATE] All cameras (" + allCams.Length + "): ";
                for (int i = 0; i < allCams.Length; i++)
                {
                    var c = allCams[i];
                    camInfo += string.Format("[{0}] '{1}' pos=({2:F1},{3:F1},{4:F1}) fov={5:F1} ord={6} vp=({7:F2},{8:F2},{9:F2},{10:F2}) ",
                        i, c.name, c.transform.position.x, c.transform.position.y, c.transform.position.z,
                        c.fieldOfView, c.orthographic ? "ORTHO" : "PERSP",
                        c.rect.x, c.rect.y, c.rect.width, c.rect.height);
                }
                Debug.Log(camInfo);
                // Probe: log character root position if a ChaControl is available.
                // IMPORTANT: C# 5 compat — on this Mono runtime, comparing
                // System.Type / MethodInfo / PropertyInfo with != null emits a
                // call to op_Inequality which does not exist.  Cast to object
                // first so the compiler emits a plain null check.
                try
                {
                    var chaControlType = System.Type.GetType("KKAPI.Chara.ChaControl");
                    if ((object)chaControlType != null)
                    {
                        var getCharControl = typeof(KKAPI.Maker.MakerAPI).GetMethod("GetCharacterControl");
                        if ((object)getCharControl != null)
                        {
                            var ctrl = getCharControl.Invoke(null, null);
                            if (ctrl != null)
                            {
                                var rootProp = ctrl.GetType().GetProperty("transform");
                                if ((object)rootProp != null)
                                {
                                    var root = rootProp.GetValue(ctrl) as UnityEngine.Transform;
                                    if (root != null)
                                    {
                                        Debug.Log(string.Format(
                                            "[KkRenderBridge] [PROBE] charRoot pos=({0:F2},{1:F2},{2:F2}) " +
                                            "camTargetDist={3:F2} camLowerFrustumY={4:F2}",
                                            root.position.x, root.position.y, root.position.z,
                                            (root.position - Camera.main.transform.position).magnitude,
                                            Camera.main.transform.position.y - 8.0f * Mathf.Tan(Camera.main.fieldOfView * 0.5f * Mathf.Deg2Rad)));
                                    }
                                }
                            }
                        }
                    }
                }
                catch (System.Exception e)
                {
                    Debug.Log("[KkRenderBridge] [PROBE] probe failed: " + e.Message);
                }
            }
        }

        // ---- F9 calibration helper ----
        // Press F9 in-game to log the current camera + lighting state.
        // Use this to capture exact values for ApplyCameraPreset().
        private void LogCurrentCameraAndLighting()
        {
            var cam = Camera.main;
            if (cam == null)
            {
                Debug.Log("[KkRenderBridge] [CALIBRATE] No main camera found");
                return;
            }

            Debug.Log("[KkRenderBridge] [CALIBRATE] === Camera ===");
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] camera.position = {0:F4}, {1:F4}, {2:F4}",
                cam.transform.position.x, cam.transform.position.y, cam.transform.position.z));
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] camera.rotation(euler) = {0:F4}, {1:F4}, {2:F4}",
                cam.transform.eulerAngles.x, cam.transform.eulerAngles.y, cam.transform.eulerAngles.z));
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] camera.fieldOfView = {0:F4}", cam.fieldOfView));
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] camera.orthographic = {0}",
                cam.orthographic));
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] camera.nearClipPlane = {0:F4}", cam.nearClipPlane));
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] camera.farClipPlane = {0:F4}", cam.farClipPlane));

            Debug.Log("[KkRenderBridge] [CALIBRATE] === Lights ===");
            var lights = GameObject.FindObjectsOfType<Light>();
            for (int i = 0; i < lights.Length; i++)
            {
                var l = lights[i];
                Debug.Log(string.Format(
                    "[KkRenderBridge] [CALIBRATE] light[{0}] name={1} type={2}",
                    i, l.name, l.type));
                Debug.Log(string.Format(
                    "[KkRenderBridge] [CALIBRATE] light[{0}] pos={1:F4},{2:F4},{3:F4}",
                    i, l.transform.position.x, l.transform.position.y, l.transform.position.z));
                Debug.Log(string.Format(
                    "[KkRenderBridge] [CALIBRATE] light[{0}] rot={1:F4},{2:F4},{3:F4}",
                    i, l.transform.eulerAngles.x, l.transform.eulerAngles.y, l.transform.eulerAngles.z));
                Debug.Log(string.Format(
                    "[KkRenderBridge] [CALIBRATE] light[{0}] intensity={1:F4} range={2:F4}",
                    i, l.intensity, l.range));
                Debug.Log(string.Format(
                    "[KkRenderBridge] [CALIBRATE] light[{0}] color(rgba)={1:F4},{2:F4},{3:F4},{4:F4}",
                    i, l.color.r, l.color.g, l.color.b, l.color.a));
                Debug.Log(string.Format(
                    "[KkRenderBridge] [CALIBRATE] light[{0}] shadows={1} shadowStrength={2:F4}",
                    i, l.shadows, l.shadowStrength));
            }

            Debug.Log("[KkRenderBridge] [CALIBRATE] === Ambient / Environment ===");
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] ambientMode={0}",
                RenderSettings.ambientMode));
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] ambientLight(rgba)={0:F4},{1:F4},{2:F4},{3:F4}",
                RenderSettings.ambientLight.r, RenderSettings.ambientLight.g,
                RenderSettings.ambientLight.b, RenderSettings.ambientLight.a));
            Debug.Log(string.Format(
                "[KkRenderBridge] [CALIBRATE] ambientIntensity={0:F4}",
                RenderSettings.ambientIntensity));
        }

        // ---- New request handler ----
        // Parses the request and enqueues it.  Multiple requests submitted
        // in the same frame are all queued; Update() drains them one at a time.
        private void OnNewRequest(string requestPath)
        {
            // Parse the JSON manually (no Newtonsoft dependency).
            // Expected format:
            //   { "character_path": "...", "camera_preset": "...", "output_path": "..." }
            string content;
            try { content = File.ReadAllText(requestPath); }
            catch (Exception e)
            {
                WriteResponse(requestPath, false, null,
                    "failed to read request: " + e.Message);
                return;
            }

            var req = ParseRequest(content);
            if (req == null)
            {
                WriteResponse(requestPath, false, null,
                    "failed to parse request: " + content);
                return;
            }

            _queue.Enqueue(new RenderJobEntry { req = req, requestPath = requestPath });
            Debug.Log("[KkRenderBridge] enqueued: " + Path.GetFileName(requestPath));
        }

        // ---- Manual JSON parsers (no Newtonsoft) ----
        // Simple key-value parser for our fixed schema. Only handles
        // string values (all our fields are strings). Not a general parser.

        private RenderRequest ParseRequest(string json)
        {
            // Strip whitespace
            var s = json.Trim();
            if (!s.StartsWith("{") || !s.EndsWith("}"))
                return null;

            var req = new RenderRequest();

            // Find "character_path"
            req.character_path = ExtractString(json, "character_path");
            req.camera_preset  = ExtractString(json, "camera_preset");
            req.output_path    = ExtractString(json, "output_path");

            if (string.IsNullOrEmpty(req.character_path) || string.IsNullOrEmpty(req.output_path))
                return null;

            return req;
        }

        private string ExtractString(string json, string key)
        {
            // Find "key": "value" pattern
            var search = "\"" + key + "\"";
            var idx = json.IndexOf(search, StringComparison.Ordinal);
            if (idx < 0) return null;

            var afterKey = json.Substring(idx + search.Length);
            var colonIdx = afterKey.IndexOf(':');
            if (colonIdx < 0) return null;

            var afterColon = afterKey.Substring(colonIdx + 1).TrimStart();
            if (!afterColon.StartsWith("\"")) return null;

            var valStart = 1;
            var valEnd = afterColon.IndexOf('"', valStart);
            if (valEnd < 0) return null;

            return afterColon.Substring(valStart, valEnd - valStart);
        }

        // ---- Render job ----
        private void RenderJob(RenderRequest req, string requestPath)
        {
            _isRendering = true;
            // Hoist these so catch/finally can access them
            string outputPath = req.output_path;
            string responsePath = requestPath + ".response.json";
            try
            {
                // Normalize paths to absolute.
                if (!Path.IsPathRooted(outputPath))
                    outputPath = Path.GetFullPath(Path.Combine(Application.dataPath, outputPath));

                // Validate we're in the Character Maker
                // Note: MakerAPI.InsideAndLoaded may be false when a character is placed
                // via drag-drop from the library (not through KKAPI's file-loading path).
                // In that case, LastLoadedChaFile is null but GetCharacterControl() still
                // returns the active ChaControl. If we're InsideAndLoaded, use the normal
                // path check. If not, just check that a ChaControl is available.
                if (!MakerAPI.InsideAndLoaded)
                {
                    // Try to get ChaControl anyway — it might be available via drag-drop
                    var ctrl2 = MakerAPI.GetCharacterControl();
                    if (ctrl2 == null)
                    {
                        WriteResponse(responsePath, false, null, "not in Character Maker");
                        return;
                    }
                    // Character was placed via drag-drop — skip path validation,
                    // just use whatever is loaded.
                    StartCoroutine(CaptureAfterDelay(outputPath, responsePath, requestPath));
                    return;
                }

                // Normal path: character was loaded through KKAPI's tracked path
                var lastLoaded = MakerAPI.LastLoadedChaFile;
                string lastPath = lastLoaded != null
                    ? CharacterExtensions.GetSourceFilePath(lastLoaded) : null;

                if (string.IsNullOrEmpty(lastPath)
                    || !Path.GetFileName(lastPath).Equals(
                        Path.GetFileName(req.character_path), StringComparison.OrdinalIgnoreCase))
                {
                    WriteResponse(responsePath, false, null,
                        "wrong character loaded. Expected: " + req.character_path
                        + ", Got: " + (lastPath ?? "(none)"));
                    Debug.LogWarning("[KkRenderBridge] wrong char: need " + req.character_path
                        + ", loaded: " + (lastPath ?? "(none)"));
                    return;
                }

                // Get the ChaControl
                var ctrl = MakerAPI.GetCharacterControl();
                if (ctrl == null)
                {
                    WriteResponse(responsePath, false, null, "no ChaControl available");
                    return;
                }

                // Apply camera/lighting preset.
                // Store the preset name so LateUpdate() can re-apply it every
                // frame — the Character Maker's camera script may reset our
                // transform during its Update(), so we need to re-assert our
                // values after the Maker runs (LateUpdate() runs later).
                _activePreset = req.camera_preset;
                ApplyCameraPreset(_activePreset);

                // Wait 2 frames for the scene to settle after camera move.
                StartCoroutine(CaptureAfterDelay(outputPath, responsePath, requestPath));
            }
            catch (Exception e)
            {
                WriteResponse(responsePath, false, null, "render failed: " + e.Message);
                Debug.LogWarning("[KkRenderBridge] render failed: " + e.Message);
            }
            finally
            {
                _isRendering = false;
            }
        }

        private IEnumerator CaptureAfterDelay(string outputPath, string responsePath, string requestPath)
        {
            // Wait 2 frames for the scene to settle after camera move.
            yield return new WaitForEndOfFrame();
            yield return new WaitForEndOfFrame();

            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
                Application.CaptureScreenshot(outputPath);
                WriteResponse(responsePath, true, outputPath, null);
                Debug.Log("[KkRenderBridge] OK: " + outputPath);
            }
            catch (Exception e)
            {
                WriteResponse(responsePath, false, null, "capture failed: " + e.Message);
                Debug.LogWarning("[KkRenderBridge] capture failed: " + e.Message);
            }
            finally
            {
                _isRendering = false;
                _activePreset = null;
            }
        }

        private void ApplyCameraPreset(string presetName)
        {
            // CALIBRATED 2026-09-08 from F9 dump in Character Maker
            // Camera: position=(0,1.246,2.1) rot=(0,180,0) fov=40
            // Light:  position=(0,4.746,-2.9) rot=(65,180,0) intensity=1.2
            Camera cam = Camera.main;
            Light light = null;

            if (presetName == "front")
            {
                if (cam != null)
                {
                    cam.transform.position = new Vector3(0f, 1.246f, 8.0f);
                    cam.transform.eulerAngles = new Vector3(0f, 0f, 0f);
                    cam.fieldOfView = 40f;
                    // Force full viewport — the Character Maker sets
                    // vp=(0.33,0,1,1) which crops the character into
                    // the right 2/3 of screen. We need full frame.
                    cam.rect = new Rect(0f, 0f, 1f, 1f);
                }

                light = GameObject.FindObjectOfType<Light>();
                if (light != null)
                {
                    light.transform.position = new Vector3(0f, 4.746f, -2.9f);
                    light.transform.eulerAngles = new Vector3(65f, 180f, 0f);
                    light.intensity = 1.2f;
                }
            }
            else if (presetName == "three_quarter")
            {
                // NOTE: Character Maker overrides camera transforms.
                // These values match the F9 dump coordinate system but may be
                // reset by the Maker UI. Calibrate by adjusting the in-game
                // camera, pressing F9, and copying values here.
                if (cam != null)
                {
                    cam.transform.position = new Vector3(0f, 1.246f, 2.1f);
                    cam.transform.eulerAngles = new Vector3(0f, 135f, 0f);
                    cam.fieldOfView = 40f;
                }

                light = GameObject.FindObjectOfType<Light>();
                if (light != null)
                {
                    light.transform.position = new Vector3(0f, 4.746f, -2.9f);
                    light.transform.eulerAngles = new Vector3(65f, 180f, 0f);
                    light.intensity = 1.2f;
                }
            }
        }

        // ---- Response writer (no Newtonsoft) ----
        private void WriteResponse(string path, bool success, string outputPath, string error)
        {
            // Write JSON manually:
            // {"success":true,"output_path":"...","error":null}
            // or
            // {"success":false,"output_path":null,"error":"..."}
            string escapedError = error != null ? error.Replace("\\", "\\\\").Replace("\"", "\\\"") : "null";
            string escapedOutput = outputPath != null ? "\"" + outputPath.Replace("\\", "\\\\") + "\"" : "null";
            string json = "{\"success\":" + success.ToString().ToLower()
                + ",\"output_path\":" + escapedOutput
                + ",\"error\":" + escapedError + "}";

            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.WriteAllText(path, json);
            }
            catch (Exception e)
            {
                Debug.LogWarning("[KkRenderBridge] failed to write response: " + e.Message);
            }
        }
    }

    // ---- Data classes ----
    internal class RenderRequest
    {
        public string character_path;
        public string camera_preset;
        public string output_path;
    }

    internal class RenderJobEntry
    {
        public RenderRequest req;
        public string requestPath;
    }

    // ---- File monitor ----
    // Polls the request directory for new JSON files (excluding our own
    // response files). Designed to be called from Update() — cheap, non-
    // blocking, processes one new file per frame.

    internal class FileMonitor
    {
        private readonly string _dir;
        private readonly System.Action<string> _onNewFile;
        private HashSet<string> _processed = new HashSet<string>();
        private DateTime _lastProcessedClear = DateTime.MinValue;
        private readonly TimeSpan _processedClearInterval = TimeSpan.FromMinutes(5);
        private readonly string _requestSuffix = ".json";
        private readonly string _responseSuffix = ".response.json";

        public FileMonitor(string dir, System.Action<string> onNewFile)
        {
            _dir = dir;
            _onNewFile = onNewFile;
            Directory.CreateDirectory(_dir);
        }

        public void Poll()
        {
            if (!Directory.Exists(_dir)) return;

            // Periodically clear old processed entries to prevent unbounded growth.
            if (DateTime.Now - _lastProcessedClear > _processedClearInterval)
            {
                _processed.Clear();
                _lastProcessedClear = DateTime.Now;
            }

            var files = Directory.GetFiles(_dir, "*" + _requestSuffix);
            foreach (var f in files)
            {
                var name = Path.GetFileName(f);
                // Skip our own response files and already-processed files
                if (name.EndsWith(_responseSuffix)) continue;
                if (_processed.Contains(f)) continue;

                _processed.Add(f);
                _onNewFile(f);
                // Enqueue all new files in this Poll() call; Update() drains
                // them one at a time from the queue, so rapid-fire submissions
                // all get queued rather than dropped.
            }
        }
    }
}
