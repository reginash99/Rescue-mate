create table transcription 
(
    id serial primary key,
    timestamp timestamp not null, 
    transcription text
);

