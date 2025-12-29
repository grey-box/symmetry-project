import { Outlet } from 'react-router-dom'
import Navbar from '@/components/Navbar'
import PageHeader from '@/components/PageHeader'

import { Textarea } from '@/components/ui/textarea'
import { Separator } from '@/components/ui/separator'

import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { text } from 'stream/consumers'

const texts = [
  {
    editing:"Born in Scranton, Pennsylvania, Biden moved with his family to Delaware in 1953.",
    reference:"Joseph Robinette Biden, Jr, commonly known as Joe Biden (/d͡ʒoʊ ˈbaɪ.dən/a), born November 20, 1942 in Scranton, Pennsylvania, is an American statesman. He settled in Delaware after leaving his hometown with his family in 1953.",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "change"
  },
  {
    
    editing:"He also oversaw six U.S. Supreme Court confirmation hearings, including the contentious hearings for Robert Bork and Clarence Thomas.",
    reference:"",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "no change"
  },
  {
    
    editing:"He also oversaw six U.S. Supreme Court confirmation hearings, including the contentious hearings for Robert Bork and Clarence Thomas.",
    reference:"",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "no change"
  },
  {
    
    editing:"He also oversaw six U.S. Supreme Court confirmation hearings, including the contentious hearings for Robert Bork and Clarence Thomas.",
    reference:"",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "no change"
  },
  {
    
    editing:"He also oversaw six U.S. Supreme Court confirmation hearings, including the contentious hearings for Robert Bork and Clarence Thomas.",
    reference:"",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "no change"
  },
  {
    
    editing:"He graduated from the University of Delaware in 1965 before earning his law degree from Syracuse University in 1968.",
    reference:"He studied at the University of Delaware before earning a law degree from Syracuse University in 1968.",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "change"
  },
  {
    
    editing:"He was elected to the New Castle County Council in 1970 and to the U.S. Senate in 1972.",
    reference:"He was elected to the county council from New Castle in 1970. At age 30, Joe Biden becomes the sixth youngest senator in the country's history, having been elected to the United States Senate in 1972.",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "change"
  },
  {
    
    editing:"As a senator, Biden drafted and led the effort to pass the Violent Crime Control and Law Enforcement Act and the Violence Against Women Act.",
    reference:"Considered a moderate Democrat, he chairs the Judiciary and Criminal Committee of the upper house of Congress from 1987 to 1995 and also chaired the Senate Foreign Affairs Committee twice between 2001 and 2009.",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "change"
  },
  {
    
    editing:"He also oversaw six U.S. Supreme Court confirmation hearings, including the contentious hearings for Robert Bork and Clarence Thomas.",
    reference:"",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "no change"
  },
  {
    
    editing:"He also oversaw six U.S. Supreme Court confirmation hearings, including the contentious hearings for Robert Bork and Clarence Thomas.",
    reference:"",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "no change"
  },
  {
    
    editing:"",
    reference:"He is the oldest president in U.S. history and the first to have a female vice presiden",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "addition"
  },
  {
    
    editing:"Biden ran unsuccessfully for the 1988 and 2008 Democratic presidential nominations.",
    reference:"Unsuccessful candidate in the Democratic primaries for the presidential election of 1988 and again in 2008,",
    suggestedContribution: "Canada has 35 million people",
    suggestionType : "change"
  },

]

const Layout = () => {
  const getColorClass = (type: any) => {
    switch (type) {
      case 'change':
        return 'bg-green-100';
      case 'addition':
        return 'bg-red-100';
      default:
        return '';
    }
  };
  
  return (

    <div className="!bg-gray-50 h-full grid grid-cols-[100px_1fr]">
      <Navbar />
      <main className="text-black bg-gray-50 py-6 px-7 flex flex-col gap-y-6">
        <PageHeader />
        <Outlet />
      </main>
    </div>
    
  //   <div>
  //   <Table>
  //   <TableHeader>
  //     <TableRow>
  //       <TableHead className="w-1/3">Referenced Article</TableHead>
  //       <TableHead>Original Article</TableHead>
  //     </TableRow>
  //   </TableHeader>
  //   <TableBody>
  //     {texts.map((text) => (
  //       <TableRow className={getColorClass(text.suggestionType)} >
  //         <TableCell className="font-medium">{text.reference}</TableCell>
  //         <TableCell>{text.editing}</TableCell>
  //       </TableRow>
  //     ))}
  //   </TableBody>
  // </Table>
      
  //   </div>
    
  )
}

export default Layout
