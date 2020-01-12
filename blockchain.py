# {
#     "index":0,
#     "timestamp":"",
#     "transactions":[
#         {
#             "sender":"",
#             "recipient":"",
#             "amount":5,
#         }
#     ],
#     "proof":"",
#     "previous_hash":"",
# }
import hashlib
import json
from argparse import ArgumentParser
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


class Blockchain:

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.new_block(proof=100, previous_hash=1)

    def register_node(self, address: str):
        # http://127.0.0.1:5001
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    # 共识，查找其他节点，选取最长的chain，如果有比现在长的，替换，没有，返回False
    def resolve_conflicts(self) -> bool:
        neighbours = self.nodes
        max_length = len(self.chain)
        new_chain = None
        for i in neighbours:
            response = requests.get(f'http://{i}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True
        return False

    # 验证chain的有效性，上一个block的哈希值是不是等于这个block的previous——hash，pow是不是符合规则
    def valid_chain(self, chain) -> bool:
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            if self.hash(last_block) != block["previous_hash"]:
                return False
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
            current_index += 1
        return True

    # 将最新的block添加进chain中，清空current，chain是个列表，每个block是个字典，字典中键transactions的值是多个字典
    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.last_block)
        }
        self.current_transactions = []
        self.chain.append(block)

        return block

    # 将交易写入current，返回当前block的序号
    def new_transcactions(self, sender, recipient, amount):
        self.current_transactions.append(
            {
                'sender': sender,
                'recipient': recipient,
                'amount': amount
            }
        )
        return self.last_block['index'] + 1

    # 静态方法，哈希函数
    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    # 返回最后一个block
    @property
    def last_block(self):
        return self.chain[-1]

    # 工作量证明
    def proof_of_work(self, last_proof: int):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        # print(proof)
        return proof

    # 工作量证明的运算，将上一个pow后加一个数使字符串的哈希值前X位为0
    def valid_proof(self, last_proof: int, proof: int) -> bool:
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        # print(guess_hash)
        return guess_hash[0:4] == "0000"
        # if guess_hash[0:4] == "0000":
        #     return  True
        # else:
        #     return  False


# 工作量证明

app = Flask(__name__)
blockchain = Blockchain()
node_identifier = str(uuid4()).replace('-', '')


@app.route('/index', methods=['GET'])
def index():
    return "Hello Blockchain"


# 向服务器传递交易信息，用new_transaction写入current
@app.route('/transaction/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    required = ["sender", 'recipient', 'amount']
    if values is None:
        return "Missing values", 400
    if not all(k in values for k in required):
        return "Missing values", 400
    index = blockchain.new_transcactions(sender=values["sender"],
                                         recipient=values["recipient"],
                                         amount=values["amount"])
    response = {'message': f'Transaction will be added to Block{index}'}
    return jsonify(response), 201


# 挖矿过程，计算自己的pow，给自己添加奖励，将自己的pow和current数据写入新的block
@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block["proof"]
    proof = blockchain.proof_of_work(last_proof)
    blockchain.new_transcactions(sender="0", recipient=node_identifier, amount=1)
    block = blockchain.new_block(proof, None)
    response = {
        "message": "New Block Forged",
        "index": block["index"],
        "transactions": block["transactions"],
        "proof": proof,
        "previous_hash": block["previous_hash"]

    }
    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


# {"nodes":["http://0.0.0.0"]}
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values['nodes']
    if nodes is None:
        return "Error:Please supply a valid of nodes", 400
    for i in nodes:
        blockchain.register_node(i)
    response = {
        "message": "New Nodes Have Been Added",
        "total_nodes": list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {
            "message": "Our Chain Is Replaced",
            "New Chain": blockchain.chain
        }
    else:
        response = {
            "message": "Our Chain Is Authoritative",
            "Chain": blockchain.chain
        }
    return jsonify(response), 200


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen to')
    args = parser.parse_args()
    port = args.port
    # -p --port
    app.run(host='0.0.0.0', port=port)
