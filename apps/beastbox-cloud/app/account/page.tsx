import type {Metadata} from 'next';
import AccountPanel from '@/components/account-panel';
export const metadata:Metadata={title:'Account · Beast Box',description:'Create a Beast Box account or keep playing as a guest.'};
export default async function AccountPage({searchParams}:{searchParams:Promise<{verified?:string}>}){const s=await searchParams;return <AccountPanel verified={s?.verified}/>;}
