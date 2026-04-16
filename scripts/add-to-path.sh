#!/bin/bash
# Add impact-vision to PATH (Mac/Linux)
# Usage: bash scripts/add-to-path.sh

SCRIPTS_DIR=$(python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>/dev/null)

if [ -z "$SCRIPTS_DIR" ]; then
    echo "Error: Python not found. Install Python 3.11+ first."
    exit 1
fi

if echo "$PATH" | grep -q "$SCRIPTS_DIR"; then
    echo "Already on PATH: $SCRIPTS_DIR"
else
    SHELL_RC=""
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_RC="$HOME/.bash_profile"
    fi

    if [ -n "$SHELL_RC" ]; then
        echo "" >> "$SHELL_RC"
        echo "# Impact Vision CLI" >> "$SHELL_RC"
        echo "export PATH=\"\$PATH:$SCRIPTS_DIR\"" >> "$SHELL_RC"
        export PATH="$PATH:$SCRIPTS_DIR"
        echo "Added to PATH in $SHELL_RC: $SCRIPTS_DIR"
    else
        export PATH="$PATH:$SCRIPTS_DIR"
        echo "Added to PATH for this session: $SCRIPTS_DIR"
        echo "To make permanent, add this to your shell config:"
        echo "  export PATH=\"\$PATH:$SCRIPTS_DIR\""
    fi
fi

echo ""
echo "============================================================"
echo "IMPORTANT: You must RESTART your terminal (close and reopen)"
echo "for the PATH change to take effect."
echo "After restarting, run: impact-vision --help"
echo "============================================================"
