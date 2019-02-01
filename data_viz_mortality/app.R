# ---
# title: "Visualization of mortality data"
# author: "Mehdi Khan"
# date: "October 2, 2018"
# output: html_document
# ---


knitr::opts_chunk$set(echo = TRUE)




# load the libraries
suppressMessages(suppressWarnings(library(ggplot2)))
suppressMessages(suppressWarnings(library(leaflet)))
suppressMessages(suppressWarnings(library(maps)))
suppressMessages(suppressWarnings(library(shiny)))
suppressMessages(suppressWarnings(library(sp)))
suppressMessages(suppressWarnings(library(plotly)))
suppressMessages(suppressWarnings(library(dplyr)))

# load data
mortData <- read.csv("./data/cleaned-cdc-mortality-1999-2010-2.csv",sep = ",", stringsAsFactors = FALSE)
stategeo <- read.csv("./data/statelatlong.csv",sep = ",", stringsAsFactors = FALSE)

causes <- unique(mortData$ICD.Chapter)
States <- unique(mortData$State)
mapStates <- map("state", fill = TRUE, plot = FALSE)

mortData$lat <- stategeo[match(mortData$State,stategeo$State),2]
mortData$long <- stategeo[match(mortData$State,stategeo$State),3]
mortData$StateFull <- stategeo[match(mortData$State,stategeo$State),4]

# create user interface
ui <-fluidPage(
 
  fluidRow(
   
   column(width = 12,align='center',
    HTML("<br><p style='text-align: center'><strong><font color='green' size='4'>Visualization of Mortality Data</font></strong><br>
<strong>Mehdi Khan</strong></p>
<br><div width=10>This Shiny page shows multiple visualizations of mortality data 
across the United States.<br> Please click on the tabs below to see the appropriate graphics"),
    tabsetPanel(
      tabPanel("Part One", value=1, 
               fluidRow(
               HTML("<br>This tab shows two visualizations 
representing the <br><font color='red', size=4><strong>crude Rates of mortality in 2010 from the user selected 'cause 
of death'.</strong></font><br> The first visualization (on the left) organizes and represents data according to the state 
ranks (based on their crude rates) and <br>the second visulization (on the right) shows the US map with states rendered by their 
respective crude rates of mortality.<br><br> <strong>Known bugs:</strong> Because of the conflicts in the projections, the marker locations and the color shades in the map are sometimes not accurate...<br><br>"),    
               
                 uiOutput("selectCause"),
                 column(6,
                        tags$div(class="header", align='left',
               tags$p("The heights of the lines are organized according to the crude rates of the states they represent. Please hover over the dots for info..... ")
              
      ),
                      conditionalPanel( condition = "output.rowno==0",
                           verbatimTextOutput("noresult")),
                            tags$head(tags$style("#noresult{color: red;
                                 font-size: 15px;
                                 font-style: bold;
                                 }"              
                                                )
                                     ),
                      conditionalPanel(condition = "output.rowno==1",
                       plotlyOutput("Question1")) 
                    ),
                  column(6,
                         tags$div(class="header", align='left',
               tags$p("The different shades of the states on the map below represnt crude rates of the states, please click on the markers for more information...")
              
      ), 
      conditionalPanel(condition = "output.rowno==1",
                      leafletOutput("ratemap",height = 350)) 
                      
                    )
               
                      )
                  ),
      
      tabPanel("Part Two", value=2,
                fluidRow(
                  HTML("<br>This tab shows two visualizations 
representing the <br><font color='red', size=4><strong>comparison between the state crude rates and national average mortality rates</strong></font><br> based on the user selection of a particular cause of death in a state.<br> The first visualization (on the left) represents the state rate and national average over the years and <br>the second visulization (on the right) shows if a state is  below or above the national average in a particular year....<br><br>"),    
                  uiOutput("selectReasons"),
                  uiOutput("selectState"),
                  column(6,
                         tags$div(class="header", align='left',
               tags$p("In the plot below the lines represent state crude rate and the national average over the years...... ")
              
      ),
                         conditionalPanel( condition = "output.rowno2==0",
                           verbatimTextOutput("noresult2")),
                            tags$head(tags$style("#noresult2{color: red;
                                 font-size: 15px;
                                 font-style: bold;
                                 }"              
                                                )
                                     ),
                      conditionalPanel(condition = "output.rowno2==1",
                         
                         plotlyOutput("Question2"))
                      ),
                  column(6,
                   tags$div(class="header", align='left',
               tags$p("In the plot below the dots appear red if the crude rates are below the national average in a particular year....")
              
      ), 
          conditionalPanel(condition = "output.rowno2==1",plotlyOutput("Question2a")))
                 )), 
      id = "tabselected"
      )
   )
  )
 
  
 )


  
  server <- function(input,output){
    
     # populate the list of causes
  output$selectCause <- renderUI({selectInput("causes", "Select a cause", choices=causes,selected = "Neoplasms", width = 600)
  })
  
  output$selectReasons <- renderUI({selectInput("reasons", "Select a cause", choices=causes,selected = "Mental and behavioural disorders", width = 600)
  })
  
  
  # populate the list of States
  output$selectState <- renderUI({ selectInput("states", "Select a State", choices=States, selected = "MD")
  })
   
    selectedCause <- reactive({input$causes}) 
    selectedState <- reactive({input$states})
    selectedReason <- reactive({input$reasons}) 
   
   
    output$rowno <- reactive(if (nrow(mortData[mortData$Year==2010 & mortData$ICD.Chapter==selectedCause(),])==0) 0 else 1)
    output$rowno2 <- reactive(if (nrow(mortData[mortData$ICD.Chapter==selectedReason() & mortData$State==selectedState(),])==0) 0 else 1)
  
    # message if no records are available
   output$noresult <- renderText({
     cause <- req(selectedCause())
     if (nrow(mortData[mortData$Year==2010 & mortData$ICD.Chapter==cause,])==0){
       txt <- paste("No record for ",cause,"in the year of 2010", sep = " ")}
       txt
   })
   
   output$noresult2 <- renderText({
     reason <- req(selectedReason())
     st <- req(selectedState())
     if (nrow(mortData[mortData$ICD.Chapter==reason & mortData$State==st,])==0){
       txt <- paste("No record for ",reason,"in", st,sep = " ")}
       txt
   })
   
   # first plot on tab 1
   output$Question1 <- renderPlotly({ 
     
     cause <- req(selectedCause())
     
     mortRate(cause)}
     )
   
   # first plot on tab 2
   output$Question2 <- renderPlotly({ 
     
     reason <- req(selectedReason())
     state_select  <- req(selectedState())
     compareMortality(reason,state_select)}
     )
   # second plot on tab 2
   output$Question2a <- renderPlotly({ 
     
     reason <- req(selectedReason())
     state_select  <- req(selectedState())
     compareDot(reason,state_select)
      #compareMortality(reason,state_select)
     }
     )
   
   
   # map on tab 1
     output$ratemap <- renderLeaflet({
     df <- mortData[mortData$Year==2010 & mortData$ICD.Chapter==selectedCause(),]
     bins <- unique(round(bin(max( df$Crude.Rate)),1))
     pal <- colorBin("YlGnBu", domain = df$Crude.Rate, bins = bins)

   m <- leaflet(data = df) %>%
          addTiles(options=providerTileOptions(noWrap = TRUE)) %>%
          setView(lng=-95.60095789311049, lat=40.2788930072988 , zoom=3.5) %>%
     
          addPolygons(lng = mapStates$x, 
                      lat = mapStates$y, 
                      #fillColor = topo.colors(10, alpha = NULL), 
                      fillColor = ~pal(Crude.Rate), 
                      stroke = FALSE) %>% 
         addMarkers (lng = ~long,
                     lat = ~lat,
                     popup = paste("Crude Rate:", df$Crude.Rate, "<br>",
                                    "State:", df$StateFull, "<br>",
                                   "Year:", "2010")) %>%
      addLegend(pal = pal, values = ~Crude.Rate, group = "circles", position = "bottomright") 
   
   
 })
 outputOptions(output, "rowno", suspendWhenHidden = FALSE) 
 outputOptions(output, "rowno2", suspendWhenHidden = FALSE)
    
  }



# function for first plot on tab 1
mortRate <- function(disease){
df <- mortData[mortData$Year==2010 & mortData$ICD.Chapter==disease,]
df$State <- factor(df$State, levels = df[order(-df$Crude.Rate),"State"])
p <- ggplot(df,aes(State,Crude.Rate))+geom_point(size = 1.5)+geom_segment(aes(x=State,xend=State, y=0,yend=Crude.Rate))+labs( x="State")+theme(axis.text.x = element_text(angle = 90,vjust = 0.25, size = 7))

ggplotly(p) %>% config(displaylogo = FALSE,
modeBarButtonsToRemove = list(
    'sendDataToCloud',
    'toImage',
    'autoScale2d',
    'resetScale2d',
    'hoverClosestCartesian',
    'hoverCompareCartesian'
))
  
}


# function for first plot on tab 2
compareMortality <- function(disease, statename){
national <- mortData %>% filter(ICD.Chapter==disease) %>%
    select(State, Year, Deaths, Population, Crude.Rate) %>%
    group_by(Year) %>% mutate(national_Avg = round((sum(Deaths) / sum(Population)) * 10^5, 1)) %>%
    select(State, Year, Crude.Rate, national_Avg) %>%  ungroup()

national <- national[national$State==statename,]

p <- ggplot(national,aes(Year))+geom_line(aes(y=Crude.Rate,colour=State), size=1)+geom_line(aes(y=national_Avg,colour="National Avg."), linetype='dashed',size=1) + labs(colour="Mortality rates") +  theme(legend.position=c(.9, 0.85),legend.title=element_text(size=10))

ggplotly(p) %>% config(displaylogo = FALSE,
modeBarButtonsToRemove = list(
    'sendDataToCloud',
    'toImage',
    'autoScale2d',
    'resetScale2d',
    'hoverClosestCartesian',
    'hoverCompareCartesian'
)) %>% layout(legend = list(orientation = "h",   # show entries horizontally
                     xanchor = "center",  # use center of legend as anchor
                     x = .72,y= .1)) 

}



# function for second plot on tab 2
compareDot <- function(disease, statename){
nationalData <- mortData %>% filter(ICD.Chapter==disease) %>%
    select(State, Year, Deaths, Population, Crude.Rate) %>%
    group_by(Year) %>% mutate(national_Avg = round((sum(Deaths) / sum(Population)) * 10^5, 1)) %>%
    select(State, Year, Crude.Rate, national_Avg) %>%  ungroup()

nationalData <- nationalData[nationalData$State==statename,]

nationalData$compareRate <- ifelse (nationalData$Crude.Rate<nationalData$national_Avg,"below","above")
#national$Year <- as.character(national$Year)
#national <- national[order(national$Crude.Rate),]
nationalData$Year <- factor(nationalData$Year, levels = nationalData$Year)
p <- ggplot(nationalData, aes(x=Crude.Rate, y=Year, label=Crude.Rate)) + 
   geom_point(stat='identity', aes(colour=compareRate), size=6)  +  geom_text(color="white", size=2)+
   scale_color_manual(name="Mortality Comparison",
                    labels = c("Above National avg.", "Below National avg."),
                    values = c("above"="darkgreen", "below"="red")) 

ggplotly(p) %>% config(displaylogo = FALSE,
modeBarButtonsToRemove = list(
    'sendDataToCloud',
    'toImage',
    'autoScale2d',
    'resetScale2d',
    'hoverClosestCartesian',
    'hoverCompareCartesian'
)) %>% layout(legend = list(orientation = "h",   
                     xanchor = "center",  
                     x = .5,y= .1))

}


bin <- function(num){
  c(0,(num/8),(num/8)*2,(num/8)*3,(num/8)*4,(num/8)*5,(num/8)*6,(num/8)*7,(num/8)*8)
  
}

 
  shinyApp(ui=ui, server = server) 




# References:
# 
# http://r-statistics.co/Top50-Ggplot2-Visualizations-MasterList-R-Code.html
# https://www.datascience.com/blog/beginners-guide-to-shiny-and-leaflet-for-interactive-mapping
