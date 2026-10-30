import type {Metadata} from 'next';
import ClassroomPanel from '@/components/classroom-panel';
export const metadata:Metadata={title:'Classroom · Beast Box',description:'Owner-only teaching thread for Zeref.',robots:{index:false,follow:false}};
export default function ClassroomPage(){return <ClassroomPanel/>;}
