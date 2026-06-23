using System;

namespace HawkinsDMS
{
    public partial class Upload : SecurePage
    {
        protected override string RequiredPermission => "upload";
        protected void Page_Load(object sender, EventArgs e)
        {

        }
    }
}