from multiprocessing.managers import BaseManager
from multiprocessing import Process, Queue
from typing import Any


class Singleton(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]



class Configuration(metaclass=Singleton):
    samplerate: int = 48000
    blocksize: int = 128
    ninputs: int = 1
    noutputs: int = 1

    def __str__(self):
        return f"{self.__class__.__name__}({self.samplerate=}, {self.blocksize=}, {self.ninputs=}, {self.noutputs=})"


_configuration = Configuration()



def spawn_config_from_process(get_config: callable, queue: Queue):
    process_config: Configuration = get_config()
    process_config.blocksize = 512
    queue.put([id(process_config), process_config])
    return


class SingleManager(BaseManager):
    pass


_queue = Queue()


SingleManager.register("config", lambda: _configuration)
SingleManager.register("queue", lambda: _queue)


if __name__ == '__main__':
    with SingleManager() as sm:
        queue: Queue = sm.queue()
        main_config = sm.config()
        process = Process(target=spawn_config_from_process, args=(sm.config, queue))
        process.start()
        process.join(1.)
        proc_id, proc_config = queue.get(timeout=1.)
        print(f"{' ': 8s} Config ID    |    Config Obj")
        print(f"Main process:  {id(main_config)}  |  {main_config}")
        print(f"Other process:  {proc_id},  {proc_config}")
