class TVMExitCode(BaseException):
    EXIT_CODES = {
        0: 'Standard successful execution exit code.',
        1: 'Alternative successful execution exit code.',
        2: 'Stack underflow. Last op-code consumed more elements than there are on the stacks.',
        3: 'Stack overflow. More values have been stored on a stack than allowed by this version of TVM.',
        4: 'Integer overflow. Integer does not fit into −2256 ≤ x < 2256 or a division by zero has occurred.',
        5: 'Integer out of expected range.',
        6: 'Invalid opcode. Instruction is unknown in the current TVM version.',
        7: 'Type check error. An argument to a primitive is of an incorrect value type.',
        8: 'Cell overflow. Writing to builder is not possible since after operation there would be more than 1023 bits or 4 references.',
        9: 'Cell underflow. Read from slice primitive tried to read more bits or references than there are.',
        10: 'Dictionary error. Error during manipulation with dictionary (hashmaps).',
        11: 'Most often caused by trying to call get-method whose id wasn\'t found in the code (missing method_id modifier or wrong get-method name specified when trying to call it). In TVM docs its described as "Unknown error, may be thrown by user programs".',
        12: 'Thrown by TVM in situations deemed impossible.',
        13: 'Out of gas error. Thrown by TVM when the remaining gas becomes negative.',
        -13: 'Contract was not found in the blockchain.',
        -14: 'It means out of gas error, same as 13. Negative, because it cannot be faked',
        32: 'Action list is invalid. Set during action phase if c5 register after execution contains unparsable object.',
        -32: '(the same as prev 32) - Method ID not found. Returned by TonLib during an attempt to execute non-existent get method.',
        33: 'Action list is too long.',
        34: 'Action is invalid or not supported. Set during action phase if current action cannot be applied.',
        35: 'Invalid Source address in outbound message.',
        36: 'Invalid Destination address in outbound message.',
        37: 'Not enough TON. Message sends too much TON (or there is not enough TON after deducting fees).',
        38: 'Not enough extra-currencies.',
        40: 'Not enough funds to process a message. This error is thrown when there is only enough gas to cover part of the message, but does not cover it completely.',
        43: 'The maximum number of cells in the library is exceeded or the maximum depth of the Merkle tree is exceeded.'
    }

    def __init__(self, code: int):
        self.code = code
        self.message = self.EXIT_CODES.get(code, 'Unknown exit code')
        super().__init__(self.message)
