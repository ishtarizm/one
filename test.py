from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen to')
args = parser.parse_args()
port = args.port
print(port)