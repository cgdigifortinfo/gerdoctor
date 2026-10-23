









import { TabsContent } from '../../../components/ui/tabs';



import EventManagement from '../../../components/admin/EventManagement';





// Stryker disable all: declarative React adapter over the tested event domain.
export function EventsTab() {
    return (
<TabsContent value="events">
                        <EventManagement />
                    </TabsContent>
    );
}
