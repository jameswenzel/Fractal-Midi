from mydy import Events, FileIO, Containers
from functools import reduce

TWELVE_ROOT_TWO = 2 ** (1 / 12)
Q_NOTE_PHRASE_LEN = 16  # number of times to repeat phrase per quarter note


def get_root(track):
    '''Gets the pitch of the first NoteOn event in a track'''
    for event in track:
        if isinstance(event, Events.NoteOnEvent):
            return event.pitch


def get_ratio(root, pitch):
    '''Calculate the ratio between two pitches'''
    # difference in semitones
    difference = pitch - root
    return TWELVE_ROOT_TWO ** (difference)


def get_note_info(track):
    '''
    Parse (note, length, wait) tuples from a track and yield them one at a time
    '''
    for i, event in enumerate(track):
        if isinstance(event, Events.NoteOnEvent):
            duration = track[i+1].tick
            yield event.pitch, duration, event.tick


def fractalize_note(resolution, ratio_fn, track, note_info):
    '''
    Given a (note, duration, tick) tuple representing a note within the supplied
    track, return a repeated and timestretched version of the track
    representing a fractal version of the note.
    Params:
        resolution: number - resolution of the track
        ratio_fn: function - function to calculate the relative frequency of the
            note we are fractalizing with regard to the root of a track
        track: mydy.Track - the track we are fractalizing
        note_info: (number, number, number) - tuple of (pitch, duration, tick)
            information, e.g. (60, 96), would be "middle c for 96 ticks"
    Returns a new mydy.Track object
    '''
    pitch, duration, tick = note_info
    quarter_notes = duration / resolution
    ratio = ratio_fn(pitch)
    repetitions = Q_NOTE_PHRASE_LEN * quarter_notes * ratio
    fract = (track / ratio) ** repetitions
    fract[0].tick = tick / resolution * track.length * Q_NOTE_PHRASE_LEN
    return fract


def fractalize_track(resolution, track):
    '''
    Given a resolution and a track containing a monophonic melody, return a
    fractalized version of that melody as a new track
    '''
    track = sort_ticks(track)
    root = get_root(track)
    note_tuples = get_note_info(track)
    header, track = split_header_meta_events(track)
    endevent = None
    if isinstance(track[-1], Events.EndOfTrackEvent):
        endevent = track[-1]
        track = track[:-1]

    def ratio_wrt_root(pitch): return get_ratio(root, pitch)

    def f_note(note_tuple): return fractalize_note(resolution, ratio_wrt_root,
                                                   track, note_tuple)

    fractal = reduce(lambda x, y: x + y,
                     (f_note(note) for note in note_tuples))
    if endevent is not None:
        fractal.append(endevent)
    fractal /= track.length / resolution * Q_NOTE_PHRASE_LEN

    return header + fractal

def fix_mary(track):
    events = []
    for event in track:
        if isinstance(event, Events.NoteOnEvent):
            if event.velocity == 0:
                events.append(Events.NoteOffEvent(tick=event.tick,
                              pitch=event.pitch,
                              velocity=event.velocity))
                continue
        events.append(event)
    return Containers.Track(events=events, relative=track.relative)


def split_header_meta_events(track):
    '''
    Split out the header MetaEvents from a track and return two tracks
    containing the header events and the body of the track.
    '''
    for i, event in enumerate(track):
        if not isinstance(event, Events.MetaEvent):
            return track[:i], track[i:]
    return Containers.Track(relative=track.relative), track


def sort_ticks(track):
    '''
    NoteOn events sometimes happen before the previous note's off event, this 
    sorts the track so NoteEvents are in On, Off order
    '''
    track = track.make_ticks_abs()
    events = sorted(track,
                    key=lambda e: e.tick * 10 +
                    isinstance(e, Events.NoteOnEvent))
    track = Containers.Track(events=events, relative=False)
    return track.make_ticks_rel()

if __name__ == '__main__':
    sotw = FileIO.read_midifile('mono_mary.mid')
    sotw_track = fix_mary(sotw[0])

    fractal = fractalize_track(sotw.resolution, sotw_track)

    FileIO.write_midifile('test3.mid', Containers.Pattern(
        resolution=sotw.resolution * 1, fmt=sotw.format, tracks=[fractal]))
    # a = FileIO.read_midifile('test2.mid')
