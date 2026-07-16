
[ConstructivePolicy](file:///home/msteindl@risc.local/repos/my_inprossa/.venv/lib/python3.11/site-packages/rl4co/models/common/constructive/base.py#L81)
- Base class for constructive policies. Constructive policies take as input and instance and output a solution (sequence of actions).
    "Constructive" means that a solution is created from scratch by the model.

[AutoregressivePolicy(ConstructivePolicy)](file:///home/msteindl@risc.local/repos/my_inprossa/.venv/lib/python3.11/site-packages/rl4co/models/common/constructive/autoregressive/policy.py#L7)
- Template class for an autoregressive policy

[class AttentionModelPolicy(AutoregressivePolicy)](file:///home/msteindl@risc.local/repos/my_inprossa/.venv/lib/python3.11/site-packages/rl4co/models/zoo/am/policy.py#L10)
- 

---

find /opt/venv/lib/python3.11/site-packages/rl4co/ -name "*.py" -exec grep '(RL4COEnvBase)' {} +

routing/cvrp/env.py:22:class CVRPEnv(RL4COEnvBase):
routing/mpdp/env.py:16:class MPDPEnv(RL4COEnvBase):
routing/mtsp/env.py:14:class MTSPEnv(RL4COEnvBase):
routing/pctsp/env.py:17:class PCTSPEnv(RL4COEnvBase):
routing/mdcpdp/env.py:13:class MDCPDPEnv(RL4COEnvBase):
routing/shpp/env.py:16:class SHPPEnv(RL4COEnvBase):
routing/mtvrp/env.py:16:class MTVRPEnv(RL4COEnvBase):
routing/pdp/env.py:13:class PDPEnv(RL4COEnvBase):
routing/svrp/env.py:15:class SVRPEnv(RL4COEnvBase):
routing/tsp/env.py:22:class TSPEnv(RL4COEnvBase):
routing/op/env.py:17:class OPEnv(RL4COEnvBase):
routing/atsp/env.py:16:class ATSPEnv(RL4COEnvBase):
eda/dpp/env.py:17:class DPPEnv(RL4COEnvBase):
scheduling/smtwtp/env.py:15:class SMTWTPEnv(RL4COEnvBase):
scheduling/ffsp/env.py:16:class FFSPEnv(RL4COEnvBase):
graph/mcp/env.py:13:class MCPEnv(RL4COEnvBase):
graph/flp/env.py:14:class FLPEnv(RL4COEnvBase):

