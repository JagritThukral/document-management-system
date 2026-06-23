const loginForm = document.getElementById('loginForm');
loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(loginForm);
    try {
        const response = await fetch(`${apiBaseURL}/auth/login`, {
            method: 'POST',
            credentials: "include",
            body: data,
        });
        const result = await response.json();
        if (!response.ok) {
            alert(result.detail)
        } else {
            document.cookie = `access_token=${result.token}; path=/; max-age=86400;SameSite=None; Secure`;
            window.location.href = '/';
        }
    }
    catch (error) {
        console.error('Error during login:', error);
        alert('An error occurred during login. Please try again.');
    }
});