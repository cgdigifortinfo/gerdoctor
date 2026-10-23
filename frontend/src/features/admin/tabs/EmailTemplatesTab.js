









import { TabsContent } from '../../../components/ui/tabs';


import EmailTemplateEditor from '../../../components/admin/EmailTemplateEditor';






// Stryker disable all: declarative React adapter over the tested email-template domain.
export function EmailTemplatesTab() {
    return (
<TabsContent value="email-templates">
                        <EmailTemplateEditor />
                    </TabsContent>
    );
}
