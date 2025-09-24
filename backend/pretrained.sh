#!/bin/sh
FILENAME="$1"
CURRENT_ID="$2"
INPUT_DIR="${3:-input_audio}"
OUTPUT_AUDIO_DIR="${4:-output_audio}"

python inference.py \
   --input_folder "$INPUT_DIR" \
   --output_folder "$OUTPUT_AUDIO_DIR" \
   --checkpoint_file ckpts/SEMamba_advanced.pth  \
   --config recipes/SEMamba_advanced/SEMamba_advanced.yaml \
   --post_processing_PCS False \
   --file "$FILENAME" \
   --current_id "$CURRENT_ID"
