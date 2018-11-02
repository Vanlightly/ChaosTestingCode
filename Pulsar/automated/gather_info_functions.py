import subprocess
import time

def get_proxy_ip():
    bash_command = "bash ../cluster/get-node-ip.sh proxy"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    ip = output.decode('ascii').replace('\n', '')
    return ip

def get_topic_owner(topic):
    bash_command = f"bash ../cluster/find-topic-owner.sh pulsar1 {topic}"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode('ascii').replace('\n', '')

def get_live_nodes():
    bash_command = "bash ../cluster/list-live-nodes.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    nodes_line = output.decode('ascii').replace('\n', '')
    return nodes_line.split(' ')

def get_live_in_zk_brokers():
    bash_command = "bash ../cluster/list-brokers.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    brokers_line = output.decode('ascii').replace('\n', '').replace('[', '').replace(']', '')
    brokers_list = brokers_line.split(', ')
    brokers = list()    
    for broker in brokers_list:
        brokers.append(broker.split(':')[0])

    return brokers

def get_live_broker():
    brokers = get_live_in_zk_brokers()
    return brokers[0]

def get_owner_broker(topic):
    live_broker = get_live_broker()
    bash_command = f"bash ../cluster/find-topic-owner.sh {live_broker} {topic}"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    owner = output.decode('ascii').replace('\n', '')
    return owner

def get_bookie_in_first_ledger():
    live_broker = get_live_broker()
    bash_command = "bash ../cluster/find-bookie-in-first-ledger.sh"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    bookie = output.decode('ascii').replace('\n', '')
    return bookie

def get_last_confirmed_entry(topic, attempt=1):
    broker = get_live_broker()
    bash_command = f"bash ../cluster/find-last-bk-entry.sh {broker} {topic}"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    lac_line = output.decode('ascii').replace('\n', '')
    print(f"LCE. broker {broker} lac_line {lac_line}")

    if "No such container" in lac_line or not lac_line:
        # most likely, zk has a stale view on the world, let it catch up and try once more
        if attempt > 3:
            print("live broker is not really live. Aborting test")
        else:
            time.sleep(5)
            attempt += 1
            return get_last_confirmed_entry(topic, attempt)

    entry = int(lac_line.split(":")[1].replace("\"", "").replace(",", ""))
    first = int(lac_line.split(":")[0].replace("\"", ""))
    return [first, entry]