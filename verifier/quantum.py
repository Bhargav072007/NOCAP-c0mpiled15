"""Grover review search, simulated locally. Measurement probabilities are not truth scores."""
import math
import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Statevector

def phase_flip(qc,index,n):
    zeros=[q for q in range(n) if not (index>>q)&1]
    for q in zeros: qc.x(q)
    if n==1: qc.z(0)
    else:
        qc.h(n-1);qc.mcx(list(range(n-1)),n-1);qc.h(n-1)
    for q in zeros: qc.x(q)

def search_batch(flags,offset=0,shots=2048,seed=17):
    n=max(1,(len(flags)-1).bit_length());size=1<<n
    marked=[i for i,f in enumerate(flags) if f.get('needs_human_review',f['status']!='VERIFIED')]
    theta=math.asin(math.sqrt(len(marked)/size)) if marked else 0
    candidates=range(max(1,int(math.pi/(4*theta))+2)) if theta else [0]
    iterations=max(candidates,key=lambda k:(math.sin((2*k+1)*theta)**2,-k)) if marked else 0
    qc=QuantumCircuit(n,name='NoCap_review_search');qc.h(range(n))
    for _ in range(iterations):
        for index in marked: phase_flip(qc,index,n)
        qc.h(range(n));phase_flip(qc,0,n);qc.h(range(n))
    probs=Statevector.from_instruction(qc).probabilities()
    counts=np.random.default_rng(seed).multinomial(shots,probs/probs.sum())
    return {'offset':offset,'qubits':n,'iterations':iterations,'marked_indices':[offset+i for i in marked],
        'baseline_marked_probability':len(marked)/size,'amplified_marked_probability':float(sum(probs[i] for i in marked)),
        'padded_probability':float(sum(probs[len(flags):])), 'padded_samples':int(sum(counts[len(flags):])), 'circuit_depth':qc.depth(),
        'circuit_qasm2':qasm2.dumps(qc),'shots':shots,'seed':seed,
        'observations':[{'flag_index':offset+i,'probability':float(probs[i]),'samples':int(counts[i]),'marked':i in marked} for i in range(len(flags))]}

def prioritize(flags,shots=2048,seed=17):
    if type(shots)!=int or not 1<=shots<=1000000:raise ValueError('shots must be 1..1000000')
    if type(seed)!=int or seed<0:raise ValueError('seed must be a nonnegative integer')
    batches=[search_batch(flags[i:i+256],i,shots,seed+i) for i in range(0,len(flags),256)]
    return {'algorithm':'Grover amplitude amplification of review flags','execution':'local Qiskit statevector simulator',
        'quantum_hardware_used':False,'truth_estimation':False,'quantum_advantage_demonstrated':False,
        'oracle':'Classically computed needs_human_review predicate; all findings retained regardless of sampling.',
        'batches':batches,'review_indices':[i for i,f in enumerate(flags) if f.get('needs_human_review',f['status']!='VERIFIED')]}
