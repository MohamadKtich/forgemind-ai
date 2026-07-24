import {NextRequest,NextResponse} from "next/server";
const protectedPrefixes=["/dashboard","/machines","/predictive-maintenance","/quality-control","/production","/alerts","/assistant","/simulation","/reports","/admin","/profile","/settings"];
export function proxy(request:NextRequest){const isProtected=protectedPrefixes.some(prefix=>request.nextUrl.pathname.startsWith(prefix));if(isProtected&&request.cookies.get("fm_session")?.value!=="1"){const url=new URL("/login",request.url);url.searchParams.set("next",request.nextUrl.pathname);return NextResponse.redirect(url)}return NextResponse.next()}
export const config={matcher:["/((?!_next/static|_next/image|favicon.ico|brand).*)"]};
