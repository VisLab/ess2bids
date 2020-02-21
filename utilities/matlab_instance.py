from matlab.engine import start_matlab
import io
import os
import os.path

__matlab_instance = None


def create_matlab_instance(eeglab_path, verbose=False):
    global __matlab_instance
    matlab_out = io.StringIO()
    matlab_err = io.StringIO()

    if not __matlab_instance:
        print('Loading Matlab engine...')

        __matlab_instance = start_matlab("-nosplash")

        try:
            __matlab_instance.addpath(eeglab_path)
        except Exception as e:
            print("Error importing EEGLAB. Check your EEGLAB installation path in 'config.json'")
            raise e
        __matlab_instance.addpath(os.path.join(os.path.dirname(os.path.abspath(__file__))), 'ess')

        print('Loading EEGLAB...')

        __matlab_instance.eeglab(stdout=matlab_out, stderr=matlab_err)
        if verbose:
            print(matlab_out.getvalue())
            print(matlab_err.getvalue())


def get_matlab_instance():
    return __matlab_instance


def teardown_matlab_instance():
    __matlab_instance.quit()
