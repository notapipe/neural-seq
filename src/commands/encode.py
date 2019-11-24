import math
from collections import defaultdict
from pathlib import Path

import music21


class Track(object):
    @staticmethod
    def encode_notes(notes, sample_freq=4, transpose=0):
        """
        Return a list-of-strings representation of the notes for downstream tasks (language modeling)
        """
        encoded = []
        for note in notes:
            # NOTE: We'll make a sort of crude approximation of the musical sequence here
            # Passing in a quantized stream will help reduce these though. Further thought required.
            duration = math.floor(note.duration.quarterLength * sample_freq)

            if isinstance(note, music21.note.Note):
                midi_pitch = note.pitch.midi + transpose
                tok = f'S-{midi_pitch}'
                encoded.append(tok)
                encoded += [f'H-{midi_pitch}' for _ in range(duration - 1)]
            elif isinstance(note, music21.note.Rest):
                encoded += ['R' for _ in range(duration)]
        return encoded

    @staticmethod
    def decode_notes(enc_notes, sample_freq=4):
        """
        Return a list of music21.note.Note/Rest instances from a list-of-strings representation sampled at the
        specified sample frequency.
        """

        notes = []
        curr_note = None
        duration_inc = 1 / sample_freq

        for enc in enc_notes:
            if 'S-' in enc:
                curr_note = music21.note.Note()
                notes.append(curr_note)
                curr_note.pitch.midi = int(enc.replace('S-', ''))
                curr_note.duration = music21.duration.Duration(duration_inc)
            elif 'H-' in enc:
                curr_note.duration.quarterLength += duration_inc
            elif 'R' in enc:
                curr_note = music21.note.Rest()
                notes.append(curr_note)
                curr_note.duration = music21.duration.Duration(duration_inc)
        return notes

    def __init__(self, name, notes):
        self.name = name
        self.notes = notes  # music21.note.Note/Rest instances

    def encode(self, transpose=0):
        return self.encode_notes(self.notes, transpose)

    def track_range(self):
        pitches = [note.pitch.midi for note in self.notes if isinstance(
            note, music21.note.Note)]
        return (min(pitches), max(pitches))

    def encode_many(self, rng=(24, 75)):
        """
        Returns a list of enccodings that fit between the provided range and preserve the original
        note relationships (if any can).
        """
        rng_min, rng_max = rng
        pitch_min, pitch_max = self.track_range()

        trans_min = rng_min - pitch_min
        trans_max = trans_min + (rng_max - pitch_max)

        encodings = []

        if (rng_max - rng_min) < (pitch_max - pitch_min):
            return encodings

        for transpose in range(trans_min, trans_max + 1):
            encodings.append(self.encode(transpose=transpose))
        return encodings


class TrackCollection(object):
    def __init__(self, tracks):
        self.tracks = tracks

    @classmethod
    def load(cls, stream, instrument_filter=None):
        note_seqs = defaultdict(list)
        for action in stream.recurse(classFilter=('Note', 'Rest')):
            instrument = action.activeSite.getInstrument()
            if instrument_filter and not instrument_filter(instrument):
                continue

            instr_name = str(instrument)
            note_seqs[instr_name].append(action)

        return cls({instr_name: Track(instr_name, notes) for intr_name, notes in note_seqs.items()})

    @classmethod
    def load_from_file(cls, fname, instrument_filter=None):
        with open(fname, 'rb') as f:
            mf = music21.midi.MidiFile()
            mf.openFileLike(f)
            mf.read()
        stream = music21.midi.translate.midiFileToStream(mf)
        return cls.load(stream, instrument_filter=instrument_filter)


def run(args):
    pass
