import subprocess

bash_command = "bash get-node-ip.sh rabbitmq1"
process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
output, error = process.communicate()

ip = output.decode('ascii').replace('\n', '')

print(ip)