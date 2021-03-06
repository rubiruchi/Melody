"""Co-simulation host.

.. moduleauthor:: Vignesh Babu <vig2208@gmail.com>
"""

import shared_buffer
from shared_buffer import *
import logger
from logger import *
import getopt
import time
import json


def extract_mappings(net_cfg_file):
    assert (os.path.isfile(net_cfg_file) == True)
    with open(net_cfg_file) as f:
        data = json.load(f)
    return data


def usage():
    print "python host.py <options>"
    print "Options:"
    print "-h or --help"
    print "-c or --netcfg-file=  Absolute path to network Cfg File <required>"
    print "-l or --log-file=     Absolute path to log File <optional>"
    print "-r or --run-time=    Run time of host in seconds before it is shut-down <optional - default forever>"
    print "-n or --project-name= Name of project folder <optional - default is test project>"
    print "-d or --id= Id of the node. Required and must be > 0"
    print "-a or --app= <Name-of-src-file containing application layer>"
    sys.exit(0)


def parseOpts():

    net_cfg_file_path = None
    host_id = None
    log_file = "stdout"
    run_time = 0
    project_name = "test"
    app_layer_file = "NONE"

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "hc:l:r:n:a:m:id:",
                                     ["help", "netcfg-file=", "log-file=", "run-time=", "project-name=",
                                      "app=", "managed_application_id=", "id="])
    except getopt.GetoptError as e:
        print (str(e))
        usage()
        return 1
    for (o, v) in opts:
        if o in ("-h", "--help"):
            usage()

        if o in ("-c", "--netcfg-file="):
            net_cfg_file_path = str(v)
        if o in ("-l", "--log-file="):
            log_file = str(v)
        if o in ("-r", "--run-time="):
            run_time = int(v)
        if o in ("-n", "--project-name="):
            project_name = str(v)
        if o in ("-d", "--id="):
            host_id = int(v)

        if o in ("-m", "--managed_application_id="):
            managed_application_id = str(v)

        if o in ("-a", "--app="):
            app_layer_file = str(v)

    assert net_cfg_file_path is not None and host_id is not None and managed_application_id is not None
    return net_cfg_file_path, log_file, run_time, project_name, host_id, app_layer_file, managed_application_id


def init_shared_buffers(run_time, shared_buf_array, log, managed_application_id):
    """Initialize shared buffers used for communication with the main Melody process

    If the shared buffers cannot be opened successfully, the co-simulation host just sleeps for the specified amount of
    run time.

    :param run_time: Running time of co-simulation host in seconds
    :type run_time: int
    :param shared_buf_array: A shared buffer array object (defined in src/core/shared_buffer.py)
    :param log: A logger object (defined in src/core/logger.py)
    :param managed_application_id: The application_id assigned to this co-simulation host
    :type managed_application_id: str
    :return: None
    """
    log.info("Buffer opened: " + managed_application_id + "-main-cmd-channel-buffer")
    result = shared_buf_array.open(bufName=managed_application_id + "-main-cmd-channel-buffer", isProxy=False)
    if result == BUF_NOT_INITIALIZED or result == FAILURE:
        log.error("Failed to open communication channel ! Not starting any threads !")
        sys.stdout.flush()
        if run_time == 0:
            while True:
                time.sleep(1)

        time.sleep(run_time)
        sys.exit(0)


def main(host_id, net_cfg_file, log_file, run_time, project_name, app_layer_file, managed_application_id):
    """Main entry point of the co-simulation host

    Starts the co-simulation host and its application layer thread.

    :param host_id: Mininet host number on which this process is run. (e.g 1 implies h1)
    :type host_id: int
    :param net_cfg_file: Absolute path of file containing a mapping of application ids to ip,port values
    :type net_cfg_file: str
    :param log_file: Absolute path of file where stdout will be logged.
    :type log_file: str
    :param run_time:  Running time of co-simulated host in seconds
    :type run_time: int
    :param project_name: Name of the project
    :type project_name: str
    :param app_layer_file: Name of the file containing application layer code for this host. If not specified, a
                           default basicHostIPC layer thread will be started for the co-simulation host. The
                           app_layer_file must be located inside src/projects/project_name
    :type app_layer_file: str
    :param managed_application_id: Name of the application assigned to this co-simulaiton host
    :type managed_application_id: str
    :return: None
    """
    powersim_ids_mapping = extract_mappings(net_cfg_file)
    with open("/tmp/application_params.json") as f:
        app_attributes = json.load(f)

    
    log = logger.Logger(log_file, "Host" + str(host_id) + ": ")

    log.info("Powersim IDS Mapping: " + str(powersim_ids_mapping))
    log.info("Managed PowerSim ID: " + str(managed_application_id))
    script_location = os.path.dirname(os.path.realpath(__file__))
    project_location = script_location + "/../projects/" + project_name + "/"

    attributes = app_attributes[managed_application_id]
    shared_buf_array = shared_buffer_array()

    if app_layer_file != "NONE":
        split_ls = app_layer_file.split('.')
        host_control_layer_override_file = split_ls[0]
        log.info("Override file name: " + host_control_layer_override_file)
        host_ipc_layer = __import__("src.projects." + str(project_name) + "." + host_control_layer_override_file,
                                  globals(), locals(), ['hostApplicationLayer'], -1)
        host_ipc_layer = host_ipc_layer.hostApplicationLayer
    else:
        host_ipc_layer = __import__("basicHostIPCLayer", globals(), locals(), ['basicHostIPCLayer'], -1)
        host_ipc_layer = host_ipc_layer.basicHostIPCLayer

    log.info("Initializing inter process communication channels ...")
    sys.stdout.flush()
    init_shared_buffers(run_time, shared_buf_array, log, managed_application_id)

    log.info("Successfully opened an inter process communication channel !")
    sys.stdout.flush()

    ipc_layer = host_ipc_layer(host_id, log_file, powersim_ids_mapping, managed_application_id, attributes)
    log.info("Waiting for start command ... ")
    sys.stdout.flush()
    recv_msg = ''
    while "START" not in recv_msg:
        dummy_id, recv_msg = shared_buf_array.read_until(managed_application_id + "-main-cmd-channel-buffer",
                                                         cool_off_time=0.1)
    ipc_layer.start()
    log.info("Signalled all threads to start ...")
    sys.stdout.flush()
    recv_msg = ''

    log.info("Waiting for stop command ...")
    sys.stdout.flush()
    while "EXIT" not in recv_msg:
        dummy_id, recv_msg = shared_buf_array.read_until(managed_application_id + "-main-cmd-channel-buffer",
                                                         cool_off_time=0.1)

    ipc_layer.cancel_thread()
    log.info("Shutting Down ... ")
    sys.stdout.flush()


if __name__ == "__main__":
    net_cfg_file_path, log_file, run_time, project_name, host_id, app_layer_file, managed_application_id = parseOpts()
    sys.exit(main(host_id, net_cfg_file_path, log_file, run_time, project_name, app_layer_file, managed_application_id))
