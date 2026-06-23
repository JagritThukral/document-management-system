using System;

namespace HawkinsDMS
{
    public partial class Documents : SecurePage
    {
        protected override string RequiredPermission => "view_documents";
        protected void Page_Load(object sender, EventArgs e)
        {

        }
    }
}