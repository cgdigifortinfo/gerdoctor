









import { TabsContent } from '../../../components/ui/tabs';



import EventManagement from '../../../components/admin/EventManagement';





// Stryker disable all: declarative React adapter over the tested event domain.
export function EventsTab(props) {
    const {  } = props;
    return (
<TabsContent value="events">
                        <EventManagement />
                    </TabsContent>
    );
}
