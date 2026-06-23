using System;

namespace HawkinsDMS
{
    public partial class Chat : SecurePage
    {
        protected override string RequiredPermission => "view_ai_chat";
        protected void Page_Load(object sender, EventArgs e)
        {

        }
    }
}