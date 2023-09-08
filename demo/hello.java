//DEPS com.github.lalyos:jfiglet:0.0.8

import com.github.lalyos.jfiglet.FigletFont;

class hello {

    public static void main(String... args) throws Exception {
        System.out.println(FigletFont.convertOneLine(
               "Hello " + ((args.length>0)?args[0]:"jbang")));  ;;
    }
}