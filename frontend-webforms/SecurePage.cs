using System;
using System.IdentityModel.Tokens.Jwt;
using System.Linq;
using System.Web;
namespace HawkinsDMS
{
    public abstract class SecurePage : System.Web.UI.Page
    {
        // Every page that inherits this class MUST declare its required permission
        protected abstract string RequiredPermission { get; }

        protected override void OnInit(EventArgs e)
        {
            HttpCookie authCookie = Request.Cookies["access_token"];

            if (authCookie == null || string.IsNullOrEmpty(authCookie.Value))
            {
                Response.Redirect("~/Login.aspx", true);
                return;
            }

            try
            {
                var handler = new JwtSecurityTokenHandler();
                var jwtToken = handler.ReadJwtToken(authCookie.Value);

                var userPermissions = jwtToken.Claims
                    .Where(c => c.Type == "permissions")
                    .Select(c => c.Value)
                    .ToList();

                if (!string.IsNullOrEmpty(RequiredPermission) && !userPermissions.Contains(RequiredPermission))
                {
                    // Authenticated, but Unauthorized
                    Response.Redirect("~/Unauthorized.aspx", true);
                }
            }
            catch (Exception)
            {
                // If the token is mangled, expired, or tampered with
                Response.Redirect("~/Login.aspx", true);
            }

            base.OnInit(e);
        }
    }
}