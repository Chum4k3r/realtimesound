#!/usr/bin/env python3
"""An example for using a stream in an asyncio coroutine.

This example shows how to create a stream in a coroutine and how to wait for
the completion of the stream.

You need Python 3.7 or newer to run this.

"""
import asyncio
from multiprocessing import shared_memory
import sys

import numpy as np
import sounddevice as sd


async def record_buffer(buffer, **kwargs):
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    idx = 0

    def callback(indata, frame_count, time_info, status):
        nonlocal idx
        if status:
            print(status)
        remainder = len(buffer) - idx
        if remainder == 0:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        indata = indata[:remainder]
        buffer[idx:idx + len(indata)] = indata
        idx += len(indata)

    stream = sd.InputStream(callback=callback, dtype=buffer.dtype,
                            channels=buffer.shape[1], **kwargs)
    with stream:
        await event.wait()


async def play_buffer(buffer, **kwargs):
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    idx = 0

    def callback(outdata, frame_count, time_info, status):
        nonlocal idx
        if status:
            print(status)
        remainder = len(buffer) - idx
        if remainder == 0:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        valid_frames = frame_count if remainder >= frame_count else remainder
        outdata[:valid_frames] = buffer[idx:idx + valid_frames]
        outdata[valid_frames:] = 0
        idx += valid_frames

    stream = sd.OutputStream(callback=callback, dtype=buffer.dtype,
                             channels=buffer.shape[1], **kwargs)
    with stream:
        await event.wait()


async def _main(frames=150_000, channels=1, dtype='float32', **kwargs):
    dtype = np.dtype(dtype)
    mem_size = frames * channels * dtype.itemsize
    memory = shared_memory.SharedMemory(create=True, size=mem_size)
    buffer = np.ndarray(shape=(frames, channels), dtype=dtype, buffer=memory.buf)
    print('recording buffer ...')
    await record_buffer(buffer, **kwargs)
    print('playing buffer ...')
    await play_buffer(buffer, **kwargs)
    print('done')
    memory.close()
    memory.unlink()



async def play_rec_buffer(play_buf, rec_buf, **kwargs):
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    rec_idx = 0
    play_idx = 0

    def callback(indata, outdata, frame_count, time_info, status):
        nonlocal rec_idx, play_idx
        if status:
            print(status)
        rec_remainder = len(rec_buf) - rec_idx
        play_remainder = len(play_buf) - play_idx
        if play_remainder == 0 or rec_remainder == 0:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop

        indata = indata[:rec_remainder]
        rec_buf[rec_idx:rec_idx + len(indata)] = indata[:rec_remainder].copy()

        valid_frames = frame_count if play_remainder >= frame_count else play_remainder
        outdata[:valid_frames] = play_buf[play_idx:play_idx + valid_frames]
        outdata[valid_frames:] = 0

        rec_idx += len(indata)
        play_idx += valid_frames

    stream = sd.Stream(callback=callback,
                       dtype=(rec_buf.dtype, play_buf.dtype),
                       channels=(rec_buf.shape[1], play_buf.shape[1]),
                       **kwargs)
    with stream:
        await event.wait()


async def main(sound, rec_channels=1, dtype='float32', **kwargs):
    dtype = np.dtype(dtype)
    frames = sound.shape[0]
    play_channels = sound.shape[1]
    play_mem_size = frames * play_channels * dtype.itemsize
    play_memory = shared_memory.SharedMemory(create=True, size=play_mem_size)
    play_buf = np.ndarray(shape=(frames, play_channels), dtype=dtype, buffer=play_memory.buf)
    play_buf[:] = sound

    rec_mem_size = frames * rec_channels * dtype.itemsize
    rec_memory = shared_memory.SharedMemory(create=True, size=rec_mem_size)
    rec_buf = np.ndarray(shape=(frames, rec_channels), dtype=dtype, buffer=rec_memory.buf)

    print('playing and recording buffer ...')
    await play_rec_buffer(play_buf, rec_buf, **kwargs)
    play_buf[:] = rec_buf

    print('playing recorded buffer ...')
    await play_buffer(play_buf, **kwargs)

    play_memory.close()
    play_memory.unlink()

    rec_memory.close()
    rec_memory.unlink()


if __name__ == "__main__":
    try:
        sound = np.random.randn(150_000, 1)
        sound /= np.max(np.abs(sound))
        asyncio.run(main(sound))
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')
