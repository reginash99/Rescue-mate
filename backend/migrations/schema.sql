Drop table if exists transcription;

CREATE TABLE transcription (
    id serial primary key,
    "timestamp" timestamp without time zone NOT NULL,
    final_transcription text,
    successful_transcription boolean,
    raw_transcr text,
    bp_preemp_transcr text,
    mamba_bp_transcr text,
    mamba_bp_preemp_transcr text,
    mamba_bp_preemp_deepfilternet_transcrp text
);

