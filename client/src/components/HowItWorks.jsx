import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function HowItWorks() {

  const features = [
    {
      title: "Want The Right Answer From Multiple PDFs?",
      description: "Let Us Simplify It For You! Upload Your PDFs, And We'll Analyze Them To Give You A Clear And Concise Summarized Answer",
      imgUrl: "/card-1-logo.svg"
    },
    {
      title: "Don't Have The Material To Find Your Answer?",
      description: "No Problem! We Deliver Accurate Answers To Your Questions Using The Latest Gemini Technology And Our Extensive Database, Ensuring You Get Exactly What You Need",
      imgUrl: "/card-2-logo.svg"
    },
    {
      title: "Now Featuring Voice Search!",
      description: "Simply Ask RAG Your Question And Get Highly Precise Answers Instantly Using Our Advanced Voice Search Technology",
      imgUrl: "/card-3-logo.svg"
    },
    {
      title: "Boost Your Productivity By 10X!",
      description: "Stop Wasting Time Searching For Answers. Simply Upload, Get What You Need Instantly, And Focus On Studying. Prioritize Quality Over Endless Searching",
      imgUrl: "/card-4-logo.svg"
    }
  ]

  return (
    <div className="p-6 bg-[#1C221C] min-h-screen" id="how-it-works">
      <h2 className="text-2xl font-bold text-white text-center mb-8">How It Works :</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-5xl mx-auto">
        {features.map((feature, index) => (
          <Card key={index} className="bg-[#0A363CB2] border-none text-white p-6 relative group hover:bg-[#0A363CB2]/100 transition-colors overflow-hidden">
            <div className={`absolute w-64 h-64 ${feature.gradient} rounded-full blur-3xl ${index % 2 === 0 ? '-top-32 -left-32' : '-top-32 -right-32'}`}></div>
            <CardHeader className="p-0 mb-4 relative z-10">
              <CardTitle className="text-lg font-medium text-center">
                {feature.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 flex flex-col relative z-10">
              <p className="text-sm text-center text-white/90 mb-8">
                {feature.description}
              </p>
              <div className="flex items-center justify-center">
                {feature.imgUrl && <img src={feature.imgUrl} alt={feature.title} className="w-1/2" />}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )}