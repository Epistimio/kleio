class TrialObserver(object):
    def started_event(self, ex_info, command, host_info, start_time,
                      config, meta_info, _id):
        pass

    def heartbeat_event(self, info, captured_out, beat_time, result):
        pass

    def completed_event(self, stop_time, result):
        pass

    def interrupted_event(self, interrupt_time, status):
        pass

    def failed_event(self, fail_time, fail_trace):
        pass
