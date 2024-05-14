class ReportBase(object):

    def __init__(self, data_path, *args, **kwargs):
        self.data_path = data_path

    def load_data(self, data=None):
        pass

    def run(self):
        pass
