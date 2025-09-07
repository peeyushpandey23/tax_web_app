// Cookie Management Utilities for User Tracking
class CookieManager {
    static COOKIE_NAME = 'tax_app_user_id';
    static COOKIE_EXPIRY_DAYS = 30;

    /**
     * Generate a unique user ID
     */
    static generateUserId() {
        return 'user_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now().toString(36);
    }

    /**
     * Set a cookie with the given name, value, and expiry days
     */
    static setCookie(name, value, days) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
        const cookieString = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
        document.cookie = cookieString;
    }

    /**
     * Get a cookie value by name
     */
    static getCookie(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }

    /**
     * Delete a cookie by name
     */
    static deleteCookie(name) {
        document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`;
    }

    /**
     * Get or create user ID for current user
     */
    static getOrCreateUserId() {
        let userId = this.getCookie(this.COOKIE_NAME);
        
        if (!userId) {
            userId = this.generateUserId();
            this.setCookie(this.COOKIE_NAME, userId, this.COOKIE_EXPIRY_DAYS);
            console.log('Created new user ID:', userId);
        } else {
            console.log('Retrieved existing user ID:', userId);
        }
        
        return userId;
    }

    /**
     * Check if user ID exists in cookies
     */
    static hasUserId() {
        return this.getCookie(this.COOKIE_NAME) !== null;
    }

    /**
     * Get current user ID (returns null if not exists)
     */
    static getCurrentUserId() {
        return this.getCookie(this.COOKIE_NAME);
    }

    /**
     * Clear user ID cookie (for logout/reset)
     */
    static clearUserId() {
        this.deleteCookie(this.COOKIE_NAME);
        console.log('User ID cookie cleared');
    }
}

// Make CookieManager available globally
window.CookieManager = CookieManager;
