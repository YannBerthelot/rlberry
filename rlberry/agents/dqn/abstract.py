from abc import ABC, abstractmethod
from gym import spaces

from rlberry.agents import Agent
from rlberry.agents.dqn.exploration import exploration_factory
from rlberry.agents.dqn.memory import ReplayMemory, Transition


class AbstractDQNAgent(Agent, ABC):
    def __init__(self, env,
                 model_kwargs=None,
                 optimizer_kwargs=None,
                 exploration_kwargs=None,
                 memory_kwargs=None,
                 n_episodes=1000,
                 loss_function="l2",
                 batch_size=100,
                 gamma=0.99,
                 device="cuda:best",
                 target_update=1,
                 double=True):
        super().__init__(env)
        self.model_kwargs = model_kwargs or {"type": "DuelingNetwork"}
        self.optimizer_kwargs = optimizer_kwargs or {}
        self.exploration_kwargs = exploration_kwargs or {}
        self.memory_kwargs = memory_kwargs or {}
        self.n_episodes = n_episodes
        self.loss_function = loss_function
        self.batch_size = batch_size
        self.gamma = gamma
        self.device = device
        self.target_update = target_update
        self.double = double

        assert isinstance(env.action_space, spaces.Discrete), \
            "Only compatible with Discrete action spaces."

        self.memory = ReplayMemory(**self.memory_kwargs)
        self.exploration_policy = exploration_factory(self.env.action_space, **exploration_kwargs)
        self.training = True
        self.steps = 0
        self.writer = None

    def fit(self, **kwargs):
        episode_rewards = []
        for episode in range(self.n_episodes):
            print("episode", episode)
            done, total_reward = False, 0
            state = self.env.reset()
            while not done:
                self.exploration_policy.step_time()
                action = self.policy(state)
                next_state, reward, done, info = self.env.step(action)
                self.record(state, action, reward, next_state, done, info)
                state = next_state
                total_reward += reward
            if self.writer:
                self.writer.add_scalar("fit/total_reward", total_reward, episode)
            episode_rewards.append(total_reward)

        return {
            "n_episodes": self.n_episodes,
            "episode_rewards": episode_rewards
        }

    def record(self, state, action, reward, next_state, done, info):
        """
            Record a transition by performing a Deep Q-Network iteration

            - push the transition into memory
            - sample a minibatch
            - compute the bellman residual loss over the minibatch
            - perform one gradient descent step
            - slowly track the policy network with the target network
        :param state: a state
        :param action: an action
        :param reward: a reward
        :param next_state: a next state
        :param done: whether state is terminal
        """
        if not self.training:
            return
        self.memory.push(state, action, reward, next_state, done, info)
        batch = self.sample_minibatch()
        if batch:
            loss, _, _ = self.compute_bellman_residual(batch)
            self.step_optimizer(loss)
            self.update_target_network()

    def policy(self, observation, **kwargs):
        """
            Act according to the state-action value model and an exploration policy
        :param observation: current obs
        :return: an action
        """
        values = self.get_state_action_values(observation)
        self.exploration_policy.update(values)
        return self.exploration_policy.sample()

    def sample_minibatch(self):
        if len(self.memory) < self.batch_size:
            return None
        transitions = self.memory.sample(self.batch_size)
        return Transition(*zip(*transitions))

    def update_target_network(self):
        self.steps += 1
        if self.steps % self.target_update == 0:
            self.target_net.load_state_dict(self.value_net.state_dict())

    @abstractmethod
    def compute_bellman_residual(self, batch, target_state_action_value=None):
        """
            Compute the Bellman Residual Loss over a batch
        :param batch: batch of transitions
        :param target_state_action_value: if provided, acts as a target (s,a)-value
                                          if not, it will be computed from batch and model (Double DQN target)
        :return: the loss over the batch, and the computed target
        """
        raise NotImplementedError

    @abstractmethod
    def get_batch_state_values(self, states):
        """
        Get the state values of several states
        :param states: [s1; ...; sN] an array of states
        :return: values, actions:
                 - [V1; ...; VN] the array of the state values for each state
                 - [a1*; ...; aN*] the array of corresponding optimal action indexes for each state
        """
        raise NotImplementedError

    @abstractmethod
    def get_batch_state_action_values(self, states):
        """
        Get the state-action values of several states
        :param states: [s1; ...; sN] an array of states
        :return: values:[[Q11, ..., Q1n]; ...] the array of all action values for each state
        """
        raise NotImplementedError

    def get_state_value(self, state):
        """
        :param state: s, an environment state
        :return: V, its state-value
        """
        values, actions = self.get_batch_state_values([state])
        return values[0], actions[0]

    def get_state_action_values(self, state):
        """
        :param state: s, an environment state
        :return: [Q(a1,s), ..., Q(an,s)] the array of its action-values for each actions
        """
        return self.get_batch_state_action_values([state])[0]

    def step_optimizer(self, loss):
        raise NotImplementedError

    def seed(self, seed=None):
        return self.exploration_policy.seed(seed)

    def reset(self, **kwargs):
        pass

    def set_writer(self, writer):
        self.writer = writer
        try:
            self.exploration_policy.set_writer(writer)
        except AttributeError:
            pass

    def action_distribution(self, state):
        values = self.get_state_action_values(state)
        self.exploration_policy.update(values)
        return self.exploration_policy.get_distribution()

    def set_time(self, time):
        self.exploration_policy.set_time(time)

    def eval(self):
        self.training = False
        self.exploration_kwargs['method'] = "Greedy"
        self.exploration_policy = exploration_factory(self.env.action_space, **self.exploration_kwargs)
