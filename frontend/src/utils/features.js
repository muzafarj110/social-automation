/**
 * Feature access control utility
 * Determines whether a user has access to a specific feature
 */

/**
 * Check if a user has access to a feature
 * @param {Object} user - The user object
 * @param {string} featureName - The feature identifier (e.g., 'profile_optimizer', 'lead_gen')
 * @returns {boolean} True if user has access, false otherwise
 */
export function hasFeature(user, featureName) {
  // Admins always have access to all features
  if (user?.is_staff || user?.is_admin) {
    return true;
  }

  // Check if feature is explicitly in available_features array
  if (user?.available_features && Array.isArray(user.available_features)) {
    return user.available_features.includes(featureName);
  }

  // Fallback: check entitlements (backward compatibility)
  if (user?.entitlements && user.entitlements[featureName] !== false) {
    return true;
  }

  return false;
}
