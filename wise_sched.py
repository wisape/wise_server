from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import (EVENT_JOB_ERROR, EVENT_JOB_EXECUTED)
from wise_task import WiseTask
from prettytable import PrettyTable
import logging

logging.basicConfig()


class WiseSched(object):
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._tasks = {}

    def __name_to_work(self, name):
        if self._tasks.has_key(name):
            return self._tasks.get(name)

        return None

    def __name_to_task(self, name):
        work = self.__name_to_work(name)
        if work is not None:
            return work[0]
        else:
            return None

    def __name_to_jog(self, name):
        work = self.__name_to_work(name)
        if work is not None:
            return work[1]
        else:
            return None

    def start(self):
        self.scheduler.start()

    def stop(self):
        self.clear_tasks()
        self.scheduler.shutdown()

    def __parse_sched_time(self, task_info):
        if task_info.get('interval'):
            _type = 'interval'
            _sched_time = eval(task_info.get('interval'))
        elif task_info.get('cron'):
            _type = 'cron'
            _sched_time = eval(task_info.get('cron'))
        else:
            # loop 0: juse do once; loop 1, restart when stoped
            _type = 'loop'
            _sched_time = 10

        return _type, _sched_time

    def add_task(self, task_info):
        if self.__name_to_task(task_info['name']):
            self.update_task(task_info)
            return

        task = WiseTask(task_info)
        t_type, t_sched_time = self.__parse_sched_time(task_info)
        if t_type != 'loop':
            param = {}
            param['func'] = task.start
            param['id'] = task_info['name']
            param['trigger'] = t_type
            param.update(t_sched_time)
            job = self.scheduler.add_job(**param)
        else:
            job = self.scheduler.add_job(
                task.start, 'interval', seconds=t_sched_time, id=task_info['name'])

        self._tasks[task.name] = [task, job]

    def del_task(self, name):
        task = self.__name_to_task(name)
        task.stop()
        self.scheduler.remove_job(name)
        self._tasks.pop(name)

    def clear_tasks(self):
        for task_name in self._tasks.keys():
            self.del_task(task_name)

    def update_task(self, task_info):
        if self._tasks.has_key(task_info['name']):
            task = self.__name_to_task(task_info['name'])
            if task is not None:
                task.update(task_info)
        else:
            self.add_task(task_info)

    def status(self):
        table = PrettyTable(['name', 'describe', 'state', 'command'])
        for task_name in self._tasks.keys():
            task = self.__name_to_task(task_name)
            table.add_row(task.status().values())
        # print table
        return table


def main():
    import time
    ws = WiseSched()
    ws.add_task({"name": '123', 'command': 'ls'})
    ws.add_task({"name": '234', 'command': 'cat /dev/random'})
    ws.start()
    time.sleep(5)
    print ws.status()
    ws.update_task({"name": '264', 'command': 'ls ../'})
    time.sleep(5)
    print ws.status()
    ws.del_task('123')
    time.sleep(5)
    print ws.status()
    ws.stop()
    time.sleep(3)
    print ws.status()


if __name__ == '__main__':
    main()
