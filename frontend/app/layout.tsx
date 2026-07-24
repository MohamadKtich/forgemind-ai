import "./globals.css";
import type {Metadata} from "next";
import {PreferencesProvider} from "@/components/preferences-provider";

export const metadata:Metadata={
  title:{default:"ForgeMind AI",template:"%s | ForgeMind AI"},
  description:"Agentic industrial intelligence platform for predictive maintenance, visual quality control, production operations, reports, alerts, and digital-twin workflows.",
  authors:[{name:"Mohamad Abdullatif Ktich",url:"https://www.linkedin.com/in/mohamad-ktich"}],
  creator:"Mohamad Abdullatif Ktich",
  publisher:"Mohamad Abdullatif Ktich",
  keywords:["industrial AI","predictive maintenance","quality control","smart manufacturing","digital twin","computer vision"],
  icons:{icon:"/brand/forgemind-mark.svg"},
  metadataBase:new URL("https://github.com/MohamadKtich/forgemind-ai")
};

export default function RootLayout({children}:{children:React.ReactNode}){
  return <html lang="en" suppressHydrationWarning><body><PreferencesProvider>{children}</PreferencesProvider></body></html>
}
