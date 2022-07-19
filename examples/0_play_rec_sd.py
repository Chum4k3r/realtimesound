from typing import Generator
import sounddevice as sd
import numpy as np

__callbacks_ended: bool = True

# define o som a ser tocado
_play_sound: Generator = (np_array for np_array in [np.array([])])

_record_duration: float = 1.
_record_samples: int = None

__statuses: list = []

__sample_count = int()

__record_buffer = np.array([])


def sound_generator() -> Generator:
    return _play_sound


def num_frames() -> int:
    return sd.default.blocksize


def num_input_channels() -> int:
    return sd.default.channels['input']


def num_output_channels() -> int:
    return sd.default.channels['output']


def register_status(status: sd.CallbackFlags) -> None:
    global __statuses
    __statuses.append(status)
    return


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    audio = audio / np.max(np.abs(audio))  # normalização: amp_range == [-1, 1]
    return audio


def root_mean_squared(audio: np.ndarray) -> float:
    return (audio**2).mean()**(0.5)

RMS = root_mean_squared


def set_audio_level(audio: np.ndarray, peak_level: float) -> np.ndarray:
    new_amp = 10**(peak_level/20)
    normalized = normalize_audio(audio)
    audio = normalized * new_amp
    return audio


def set_stream_finished(finished: bool) -> None:
    global __callbacks_ended
    __callbacks_ended = finished
    return


def streaming_has_finished() -> bool:
    return __callbacks_ended


def sound_frames_generator(sound: np.ndarray, num_frames: int):
    num_channels = sound.shape[1]
    blocks_count: int = int(np.ceil(sound.shape[0] / num_frames))
    sound_gen = sound.copy()
    sound_gen.resize((blocks_count, num_frames, num_channels))
    for sound_frame in sound_gen:
        yield sound_frame


def set_play_sound(new_sound: np.ndarray) -> np.ndarray:
    global _play_sound
    _play_sound = sound_frames_generator(new_sound, num_frames())
    return


def play_callback(output_buffer: np.ndarray, num_frames: int, time_info: object, stream_status: sd.CallbackFlags) -> None:
    try:
        output_buffer[:] = next(sound_generator())
        print(f"\r{RMS(output_buffer)=}\r",end='\r')
        if stream_status is not None:
            register_status(stream_status)
    except StopIteration:
        raise sd.CallbackStop()


def check_args(**kwargs) -> list:
    returns = []
    for name, value in kwargs.items():
        if value is None:
            value = getattr(sd.default, name)
        returns.append(value)
    return returns


def set_record_duration(duration: float) -> None:
    global _record_duration, __record_buffer, _record_samples
    _record_duration = duration
    _record_samples = duration * sd.default.samplerate
    __record_buffer = make_buffer(_record_duration, sd.default.samplerate, sd.default.channels['input'], sd.default.dtype['input'])
    return


def makeup_duration(duration: float) -> int:
    return int((1.5 * duration) + 0.05)


def make_buffer(duration: float, samplerate: int, nchannels: int, dtype: np.dtype = np.float32) -> np.ndarray:
    buffer = np.zeros((makeup_duration(duration) * samplerate, nchannels), dtype=dtype)
    return buffer


class RecordTimeout(Exception):
    pass


def record_next_chunk(inbuffer: np.ndarray) -> None:
    global __record_buffer, __sample_count, _record_samples
    should_rec = min(inbuffer.shape[0], (_record_samples - __sample_count))
    __record_buffer[__sample_count:(__sample_count+should_rec)] = inbuffer[:should_rec]
    __sample_count += should_rec
    print(f"\r{RMS(inbuffer)=}\r",end='\r')
    return __sample_count < _record_samples


def record_callback(input_buffer, num_frames, time_info, status):
    if status is not None:
        register_status(status)
    keep_going = record_next_chunk(input_buffer)
    if not keep_going:
        raise sd.CallbackStop()


def record(duration: float,
           samplerate: int = None,
           num_input_channels: int = None,
           device: tuple[int, int] = None,
           buffer_size: int = None) -> np.ndarray:

    samplerate, num_input_channels, device, buffer_size = check_args(samplerate=samplerate, channels=num_input_channels, device=device, blocksize=buffer_size)

    set_record_duration(duration)

    with sd.InputStream(
                samplerate=samplerate,
                blocksize=buffer_size,
                device=device,
                channels=num_input_channels,
                dtype=np.float32,
                latency='low',
                extra_settings=None,
                callback=record_callback,
                finished_callback=(lambda: set_stream_finished(True))
            ) as stream:
        run_stream(stream)
    return __record_buffer\


def run_stream(stream: sd._StreamBase) -> None:
    set_stream_finished(False)
    while not streaming_has_finished():
        if not stream.active:
            stream.stop()
        if stream.stopped and not streaming_has_finished():
            set_stream_finished(True)
        else:
            sd.sleep(100)
    return


def play(sound: np.ndarray,
         samplerate: int = None,
         num_output_channels: int = None,
         device: tuple[int, int] = None,
         buffer_size: int = None) -> None:

    samplerate, num_output_channels, device, buffer_size = check_args(samplerate=samplerate, channels=num_output_channels, device=device, blocksize=buffer_size)
    set_play_sound(sound)

    with sd.OutputStream(
                samplerate=samplerate,
                blocksize=buffer_size,
                device=device,
                channels=num_output_channels,
                dtype=np.float32,
                latency='low',
                extra_settings=None,
                callback=play_callback,
                finished_callback=(lambda: set_stream_finished(True))
            ) as stream:
        run_stream(stream)
    return



if __name__ == '__main__':

    sd.default.device = 13, 11
    sd.default.channels = 2, 2
    sd.default.samplerate = 48000
    sd.default.blocksize = 256
    sd.default.dtype = 'float32'

    noise = np.random.randn(3 * sd.default.samplerate, num_output_channels())
    noise = set_audio_level(noise, -10)

    some_noise = record(2, num_input_channels=num_input_channels())

    play(noise, num_output_channels=num_output_channels())
