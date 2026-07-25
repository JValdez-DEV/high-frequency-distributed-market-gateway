#!/bin/bash
# ==============================================================================
# SILO B VALIDATION ARCHIVER
# ==============================================================================

# Define paths
PROJECT_DIR="/root/trade_hunter"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
ARCHIVE_DIR="${PROJECT_DIR}/archive_silo_b_${TIMESTAMP}"

echo "Initializing archive sequence for Silo B..."

# Create unique snapshot directory
mkdir -p "$ARCHIVE_DIR"

# Target incoming validation files
TARGET_FILES=(
    "graduation_report.json"
    "backtest_ledger.csv"
    "backtest_visualized.csv"
    "v3_backtest_results.txt"
)

# Move files to archive if they exist
for file in "${TARGET_FILES[@]}"; do
    if [ -f "${PROJECT_DIR}/${file}" ]; then
        cp "${PROJECT_DIR}/${file}" "$ARCHIVE_DIR/"
        echo "[SUCCESS] Captured: ${file}"
    else
        echo "[NOT FOUND] ${file} - skipping or not yet generated."
    fi
done

# Optional: Snapshot the live state configuration used during the test
if [ -f "${PROJECT_DIR}/crypto_config.json" ]; then
    cp "${PROJECT_DIR}/crypto_config.json" "$ARCHIVE_DIR/config_snapshot.json"
    echo "[SNAPSHOT] Captured active config parameters."
fi

echo "Archive sequence complete. Target directory: ${ARCHIVE_DIR}"
