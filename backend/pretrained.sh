FILENAME="$1"

python inference.py \
   --input_folder input_audio \
   --output_folder output_audio \
   --checkpoint_file ckpts/SEMamba_advanced.pth  \
   --config recipes/SEMamba_advanced/SEMamba_advanced.yaml \
   --post_processing_PCS False \
   --file "$FILENAME"
