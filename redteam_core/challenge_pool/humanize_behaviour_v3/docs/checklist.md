# Checklist for new challenge

1. Action list should randomly generated for 5 times. Just need to number of `N_CHALLENGES_PER_EPOCH` in controller.
2. Run bot.py for 3 times in each iteration which means we will make 15 session each time.
3. Collect all metrics in `_eval` endpoint.
    - Make Global variable to collect each session metrics
    ```json
        [
            {
                "data":[...],
                "action_list":[...]
            },
            
            {
                "data":[...],
                "action_list":[...]
            },
            
            {
                "data":[...],
                "action_list":[...]
            }
        ]
    ```
    - `action_list` should be hashed str, because it just needed to use for session comparison.
    - pass all collected metrics into scoring endpoint.
4. Add trajectory similarity into scoring
5. Make one scoring submodule to score `trajectory similarity` . This  submodule should be able to score 5 session, it has to retrieve same session information from hash of `action_list`

- [ ] Generate action list randomly in each iteration
- [ ] Run challenge 5 times
- [ ] Run bot.py|bot_container 3 times
- [ ] Collect same metrics in `_eval` endpoint
