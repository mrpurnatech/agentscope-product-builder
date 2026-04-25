Analyze and optimize API cost configuration.

Steps:
1. Read `core/gateway.py` — review pricing table, routing rules, and fallback chains
2. Read all agents — check `task_type` assignments and `max_tokens` values
3. Read `config/settings.py` — review token limits
4. Identify cost optimization opportunities:
   - Are any agents using a more expensive model tier than needed?
   - Are `max_tokens` limits set too high for any agent?
   - Could any sequential agent calls be parallelized?
5. Calculate estimated cost per build (assuming ~8 files in a typical plan)
6. Report recommendations with estimated savings
