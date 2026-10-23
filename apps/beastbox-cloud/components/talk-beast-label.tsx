'use client';
import {useActiveBeastName} from './use-active-beast-name';
/** "Talk to {beast}" from the single beast-name source; "Talk to My Beast" until a beast exists. */
export default function TalkBeastLabel(){const name=useActiveBeastName();return <>{name&&name!=='your beast'?`Talk to ${name}`:'Talk to My Beast'}</>;}
