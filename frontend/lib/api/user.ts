import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UserPreferences {
  theme?: "light" | "dark" | "system";
  language?: "en" | "tr";
  timezone?: string;
}

export interface PasswordChangeData {
  current_password: string;
  new_password: string;
}

/**
 * Get current user's preferences
 */
export async function getUserPreferences(token: string) {
  const response = await axios.get(`${API_URL}/users/me/preferences`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data.preferences;
}

/**
 * Update current user's preferences
 */
export async function updateUserPreferences(
  token: string,
  preferences: UserPreferences
) {
  const response = await axios.put(
    `${API_URL}/users/me/preferences`,
    preferences,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
}

/**
 * Change current user's password
 */
export async function changePassword(
  token: string,
  passwordData: PasswordChangeData
) {
  const response = await axios.put(
    `${API_URL}/users/me/password`,
    passwordData,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
}
