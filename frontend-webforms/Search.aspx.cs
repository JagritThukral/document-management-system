using System;

namespace HawkinsDMS
{
    public partial class Search : SecurePage
    {
        protected override string RequiredPermission => "search";

        protected void Page_Load(object sender, EventArgs e)
        {
        }
    }
}