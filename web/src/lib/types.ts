export interface AnalysisOptions {
  methods: string[];
  llm_available: boolean;
  llm_provider: string;
  llm_model: string;
  dataset: string;
  dataset_has_labels: boolean;
}

export interface AnalysisRequest {
  theme: string;
  keywords: string[] | null;
  method: string;
  n_topics: number | null;
  n_subtopics: number | null;
  depth: number;
  max_tweets: number;
  since: string | null;
  until: string | null;
  use_llm: boolean;
  evaluate: boolean;
}

export interface Topic {
  path: string;
  name: string;
  description: string;
  level: number;
  n_tweets: number;
  share_of_parent: number;
  share_of_total: number;
  sample_tweet_ids: string[];
}

export interface TweetAssignment {
  id: string;
  topic_path: string;
  topic: string;
  subtopic: string;
  text: string;
}

export interface RunStats {
  seconds: number;
  n_tweets: number;
  llm_calls: number;
  llm_cache_hits: number;
}

export interface ClusterMetrics {
  n?: number;
  ari?: number;
  nmi?: number;
  matched_accuracy?: number;
  matching?: Record<string, string>;
  n_pred?: number;
  n_gold?: number;
}

export interface EvaluationMetrics {
  topics?: ClusterMetrics | null;
  subtopics?: ClusterMetrics | null;
}

export interface AnalysisResult {
  theme: string;
  method: string;
  llm: string | null;
  keywords: string[];
  stats: RunStats;
  topics: Topic[];
  assignments: TweetAssignment[];
  metrics: EvaluationMetrics | null;
}
