/** Single source for the kid-and-parent journey steps. Short labels, concrete hints. */
export type JourneyStep={key:string;label:string;hint:string;href:string};
export const JOURNEY_STEPS:JourneyStep[]=[
 {key:'meet',label:'Meet',hint:'Say hello to a little Beast.',href:'/spark/index.html'},
 {key:'name',label:'Name',hint:'Give your Beast its own name.',href:'/spark/index.html'},
 {key:'play',label:'Play',hint:'Visit the habitat and have fun.',href:'/beast-cage'},
 {key:'talk',label:'Talk',hint:'Ask questions, hear answers.',href:'/beast-cage/talk'},
 {key:'rest',label:'Rest',hint:'Let your Beast take a quiet pause.',href:'/beast-cage'},
 {key:'explore',label:'Explore',hint:'Enter the LOST COSMOS adventure.',href:'/sol-game'},
 {key:'save',label:'Save',hint:'Keep your Beast for next time.',href:'/spark/index.html'},
];
