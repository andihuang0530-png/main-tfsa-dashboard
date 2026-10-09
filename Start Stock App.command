#!/bin/zsh

set -u

PROJECT_DIR="/Users/andihuang/Documents/main-tfsa-dashboard"

echo "Starting Stock App..."
echo "Project folder: $PROJECT_DIR"
echo

cd "$PROJECT_DIR" || {
  echo "Could not cd into the project folder."
  echo "Check that this folder still exists:"
  echo "$PROJECT_DIR"
  echo
  printf "Press Return to close this Terminal window..."
  read -r _
  exit 1
}

APP_URL=""
START_CMD=()
FRAMEWORK="Unknown"

if [[ -f "package.json" ]]; then
  echo "Detected package.json."

  if [[ ! -d "node_modules" ]]; then
    echo "node_modules not found. Running npm install first..."
    if ! command -v npm >/dev/null 2>&1; then
      echo "npm is not installed or not available in PATH."
      echo "Install Node.js first, then double-click this shortcut again."
      echo
      printf "Press Return to close this Terminal window..."
      read -r _
      exit 1
    fi
    npm install || {
      echo
      echo "npm install failed. See the error above."
      printf "Press Return to close this Terminal window..."
      read -r _
      exit 1
    }
  else
    echo "node_modules exists. Skipping npm install."
  fi

  DEV_SCRIPT="$(grep -E '"dev"[[:space:]]*:' package.json | head -n 1)"
  PORT=""

  if [[ "$DEV_SCRIPT" =~ "--port[ =]([0-9]+)" ]]; then
    PORT="${match[1]}"
  elif [[ "$DEV_SCRIPT" =~ "-p[[:space:]]*([0-9]+)" ]]; then
    PORT="${match[1]}"
  elif [[ -f "vite.config.js" || -f "vite.config.ts" || -f "vite.config.mjs" || -f "vite.config.cjs" || "$(grep -c '"vite"' package.json)" -gt 0 ]]; then
    FRAMEWORK="Vite"
    PORT="5173"
  elif [[ -f "next.config.js" || -f "next.config.mjs" || -f "next.config.ts" || "$(grep -c '"next"' package.json)" -gt 0 ]]; then
    FRAMEWORK="Next.js"
    PORT="3000"
  else
    FRAMEWORK="Node dev server"
    PORT="3000"
  fi

  [[ "$FRAMEWORK" == "Unknown" ]] && FRAMEWORK="Node app"
  APP_URL="http://localhost:${PORT}"
  START_CMD=(npm run dev)
else
  echo "No package.json found. Skipping node_modules/npm install check."

  if [[ -f "backend/server.py" ]]; then
    FRAMEWORK="Python stdlib web server"
    PORT="$(grep -E 'def run\(.*port: int = [0-9]+' backend/server.py | sed -E 's/.*port: int = ([0-9]+).*/\1/' | head -n 1)"
    [[ -z "$PORT" ]] && PORT="8000"
    APP_URL="http://127.0.0.1:${PORT}"
    START_CMD=(python3 -B backend/server.py)
  else
    echo "Could not detect a supported startup command."
    echo "Expected package.json for a Node app or backend/server.py for this MVP."
    echo
    printf "Press Return to close this Terminal window..."
    read -r _
    exit 1
  fi
fi

echo "Detected app type: $FRAMEWORK"
echo "Startup command: ${START_CMD[*]}"
echo "Local URL: $APP_URL"
echo
echo "Starting server. Press Control + C to stop it."
echo

(
  sleep 2
  echo "Opening browser: $APP_URL"
  open "$APP_URL" >/dev/null 2>&1 || {
    echo "Could not open the browser automatically."
    echo "Open this URL manually:"
    echo "$APP_URL"
  }
) &

"${START_CMD[@]}"
STATUS=$?

echo
echo "Stock App stopped with exit code $STATUS."
printf "Press Return to close this Terminal window..."
read -r _
