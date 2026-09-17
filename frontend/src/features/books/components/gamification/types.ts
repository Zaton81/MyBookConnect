export interface ReadingGoalData {
  year: number;
  target_books: number;
  target_pages: number;
  current_books: number;
  remaining_books: number;
  percentage: number;
  pacing_status: 'ahead' | 'on_track' | 'behind' | 'completed' | 'inactive';
  pacing_text: string;
  has_goal: boolean;
}

export interface ReadingStreakData {
  current_streak: number;
  longest_streak: number;
  last_reading_date: string | null;
  read_today: boolean;
}

export interface BadgeItem {
  id: number;
  slug: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  category_display: string;
  points: number;
  unlocked: boolean;
  awarded_at: string | null;
}

export interface ChallengeItem {
  id: number;
  slug: string;
  title: string;
  description: string;
  challenge_type: string;
  target_count: number;
  current_progress: number;
  percentage: number;
  is_completed: boolean;
  completed_at: string | null;
  start_date: string;
  end_date: string;
  is_active: boolean;
  badge_reward: {
    name: string;
    icon: string;
  } | null;
}

export interface GamificationOverviewData {
  gamification_enabled: boolean;
  detail?: string;
  streak?: ReadingStreakData;
  goal?: ReadingGoalData;
  badges?: {
    total_badges: number;
    unlocked_count: number;
    total_points: number;
    list: BadgeItem[];
  };
  challenges?: ChallengeItem[];
}
