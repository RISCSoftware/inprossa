# Bin packing - MuZero config (ptree / pure-Python MCTS for development)
#
# Switch to ctree for full training runs by setting:
#   main_config.policy.mcts_ctree = True
#
# Observation shape  : 2 * max_items  (space_left || item_sizes, each sorted desc)
# Action space size  : max_items      (bin index 0..n_open-1, or n_open = new bin)

from easydict import EasyDict

# -----------------------------------------------------------------------
# Frequently tuned knobs
# -----------------------------------------------------------------------
max_items          = 10           # fixes obs dim and action space
obs_shape          = 2 * max_items
action_space_size  = max_items

collector_env_num  = 8
n_episode          = 8
evaluator_env_num  = 3
num_simulations    = 50
update_per_collect = 200
batch_size         = 256
max_env_step       = int(2e5)
reanalyze_ratio    = 0.0
# -----------------------------------------------------------------------

bin_packing_muzero_config = dict(
    exp_name=(
        f'data_mz_ptree/bin_packing_muzero'
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
        collector_env_num=collector_env_num,
        evaluator_env_num=evaluator_env_num,
        n_evaluator_episode=evaluator_env_num,
        manager=dict(shared_memory=False),
    ),
    policy=dict(
        model=dict(
            observation_shape=obs_shape,
            action_space_size=action_space_size,
            model_type='mlp',
            lstm_hidden_size=128,
            latent_state_dim=128,
            self_supervised_learning_loss=True,
            discrete_action_encoding_type='one_hot',
            norm_type='BN',
        ),
        # ---- tree backend ----
        mcts_ctree=False,   # False → ptree (pure Python); True → ctree (C++/Cython)

        cuda=False,
        env_type='not_board_games',
        # 'varied_action_space' activates the action_mask every step
        action_type='varied_action_space',
        # max episode length = max_items steps (one item per step)
        game_segment_length=max_items,

        update_per_collect=update_per_collect,
        batch_size=batch_size,
        optim_type='Adam',
        lr_piecewise_constant_decay=False,
        learning_rate=3e-3,
        ssl_loss_weight=2,          # self-supervised loss weight
        num_simulations=num_simulations,
        reanalyze_ratio=reanalyze_ratio,
        n_episode=n_episode,
        eval_freq=int(1e3),
        replay_buffer_size=int(1e5),
        collector_env_num=collector_env_num,
        evaluator_env_num=evaluator_env_num,
    ),
)

bin_packing_muzero_config = EasyDict(bin_packing_muzero_config)
main_config = bin_packing_muzero_config

bin_packing_muzero_create_config = dict(
    env=dict(
        type='bin_packing',
        import_names=['bin_packing_mcts.envs.bin_packing_env'],
    ),
    env_manager=dict(type='subprocess'),
    policy=dict(
        type='muzero',
        import_names=['lzero.policy.muzero'],
    ),
)

bin_packing_muzero_create_config = EasyDict(bin_packing_muzero_create_config)
create_config = bin_packing_muzero_create_config
