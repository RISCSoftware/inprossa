# Bin packing - AlphaZero config (ptree / pure-Python MCTS for development)
#
# Switch to ctree for full training runs by setting:
#   main_config.policy.mcts_ctree = True
#   main_config.env.alphazero_mcts_ctree = True
#
# Observation layout : (1, 2, max_items)
#   channel 0, row 0 : space_left  per open bin  (sorted desc, zero-padded)
#   channel 0, row 1 : item sizes still to place  (sorted desc, zero-padded)
#
# NOTE: the bin-packing env currently returns a flat (2*max_items,) vector.
#       For AlphaZero the env (or a thin wrapper) must reshape it to
#       (1, 2, max_items) before returning from step() / reset().

from easydict import EasyDict

# -----------------------------------------------------------------------
# Frequently tuned knobs
# -----------------------------------------------------------------------
max_items          = 10           # fixes obs dim and action space
action_space_size  = max_items
# (C, H, W) — single channel, two rows (space_left + item_sizes), max_items cols
obs_shape          = (1, 2, max_items)

collector_env_num  = 8
n_episode          = 8
evaluator_env_num  = 3
num_simulations    = 50
update_per_collect = 200
batch_size         = 256
max_env_step       = int(2e5)
# -----------------------------------------------------------------------

bin_packing_alphazero_config = dict(
    exp_name=(
        f'data_az/bin_packing_alphazero'
        f'_ns{num_simulations}'
        f'_upc{update_per_collect}'
        f'_seed0'
    ),
    env=dict(
        env_id='bin_packing',
        max_items=max_items,
        min_items=3,
        max_item_size=0.9,
        min_item_size=0.1,
        # AlphaZero single-player mode (no adversarial opponent)
        battle_mode='single_player_mode',
        # Match the reshaped observation the env must provide
        channel_last=False,
        collector_env_num=collector_env_num,
        evaluator_env_num=evaluator_env_num,
        n_evaluator_episode=evaluator_env_num,
        manager=dict(shared_memory=False),
        # AlphaZero tree backend (must mirror policy.mcts_ctree)
        alphazero_mcts_ctree=False,
        # Simulation env settings (used internally by the policy during MCTS)
        agent_vs_human=False,
        prob_random_agent=0,
        prob_expert_agent=0,
        scale=True,
        save_replay_gif=False,
        replay_path_gif='./replay_gif',
    ),
    policy=dict(
        model=dict(
            observation_shape=obs_shape,      # (C, H, W) = (1, 2, max_items)
            action_space_size=action_space_size,
            num_res_blocks=1,
            num_channels=32,
            value_head_channels=16,
            policy_head_channels=16,
            value_head_hidden_channels=[32],
            policy_head_hidden_channels=[32],
            norm_type='BN',
        ),
        # ---- tree backend ----
        mcts_ctree=False,   # False → ptree (pure Python); True → ctree (C++/Cython)

        cuda=False,
        # Required by AlphaZero policy to build simulation envs for MCTS
        simulation_env_id='bin_packing',
        simulation_env_config_type='single_player_mode',

        update_per_collect=update_per_collect,
        batch_size=batch_size,
        optim_type='Adam',
        lr_piecewise_constant_decay=False,
        piecewise_decay_lr_scheduler=False,
        learning_rate=3e-3,
        weight_decay=1e-4,
        grad_clip_value=0.5,
        value_weight=1.0,
        entropy_weight=0.0,
        n_episode=n_episode,
        eval_freq=int(1e3),
        mcts=dict(num_simulations=num_simulations),
        other=dict(
            replay_buffer=dict(
                replay_buffer_size=int(1e5),
                save_episode=False,
            )
        ),
        collector_env_num=collector_env_num,
        evaluator_env_num=evaluator_env_num,
    ),
)

bin_packing_alphazero_config = EasyDict(bin_packing_alphazero_config)
main_config = bin_packing_alphazero_config

bin_packing_alphazero_create_config = dict(
    env=dict(
        type='bin_packing',
        import_names=['bin_packing_mcts.envs.bin_packing_env'],
    ),
    env_manager=dict(type='subprocess'),
    policy=dict(
        type='alphazero',
        import_names=['lzero.policy.alphazero'],
    ),
    collector=dict(
        type='episode_alphazero',
        import_names=['lzero.worker.alphazero_collector'],
    ),
    evaluator=dict(
        type='alphazero',
        import_names=['lzero.worker.alphazero_evaluator'],
    ),
)

bin_packing_alphazero_create_config = EasyDict(bin_packing_alphazero_create_config)
create_config = bin_packing_alphazero_create_config
