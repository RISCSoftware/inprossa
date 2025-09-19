// ----------------------------------------------------------------------------
// Simulation of a wood cutting machine.
// Copyright (C) 2025, Wolfgang Schreiner <Wolfgang.Schreiner@risc.jku.at>
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License along
// with this program; if not, see <https://www.gnu.org/licenses/>.
// ----------------------------------------------------------------------------

import java.util.*;
import java.util.function.*;
import java.io.*;

import com.fasterxml.jackson.core.*;
import com.fasterxml.jackson.databind.*;

public class WoodCutter
{
  // last input line read
  private static String lastLine = null;
  
  public static void main(String[] args)
  {
    if (args.length < 1 || args.length > 2)
    {
      System.out.println("Usage: WoodCutter <path> [ <number> ]");
      System.out.println("<path>: path of wood cutting problem file");
      System.out.println("<number>: number of beams to be scanned initially (default: 0)");
      System.exit(-1);
    }
    try
    {
      initialize(args[0]);
      if (args.length > 1)
      {
        int n = Integer.valueOf(args[1]);
        for (int i = 0; i < n; i++) execute(COMMAND_SCAN);
      }
      System.out.println(machineState.jsonString());
      execute();
    }
    catch(NumberFormatException e)
    {
      System.out.println(RESPONSE_ERROR + 
          ": invalid argument <number> (" + args[1] + ")");
      System.exit(-1);
    }
    catch(RuntimeException e)
    {
      System.out.println(RESPONSE_ERROR + 
          (lastLine == null ? "" : "(" + lastLine + ")") +
          ": " + e.getMessage());
      System.exit(-1);
    }
  }

  private static void check(boolean condition, String error) 
  {
    if (condition) return;
    throw new RuntimeException(error);
  }
  
  // --------------------------------------------------------------------------
  //
  // constants
  //
  // --------------------------------------------------------------------------

  // JSON keys in problem file
  private static final String KEY_BEAM_CONFIGURATION = "BeamConfiguration";
  private static final String KEY_BEAM_LENGTH = "BeamLength";
  private static final String KEY_NUMBER_OF_LAYERS = "NumberOfLayers";
  private static final String KEY_NUMBER_OF_BEAMS = "NumberOfBeams";
  private static final String KEY_BEAM_SKIP_START = "BeamSkipStart";
  private static final String KEY_BEAM_SKIP_END = "BeamSkipEnd";
  private static final String KEY_MIN_LENGTH_OF_BOARD_IN_LAYER = "MinLengthOfBoardInLayer";
  private static final String KEY_GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS = "GapToBoardAbutInConsecutiveLayers";
  private static final String KEY_MAX_SHIFT_CURVED_CUT = "MaxShiftCurvedCut";
  private static final String KEY_STATIC_FORBIDDEN_ZONES = "StaticForbiddenZones";
  private static final String KEY_BEGIN = "Begin";
  private static final String KEY_END = "End";
  private static final String KEY_INPUT_BOARDS = "InputBoards";
  private static final String KEY_RAW_BOARD = "RawBoard";
  private static final String KEY_ID = "Id";
  private static final String KEY_LENGTH = "Length";
  private static final String SCAN_BOARD_PARTS = "ScanBoardParts";
  private static final String KEY_START_POSITION = "StartPosition";
  private static final String KEY_END_POSITION = "EndPosition";
  private static final String KEY_QUALITY = "Quality";
  
  // additional JSON keys for machine state
  private static final String KEY_MACHINE_STATE = "MachineState";
  private static final String KEY_BOARD_INDEX = "BoardIndex";
  private static final String KEY_BOARD_BUFFER = "BoardBuffer";
  private static final String KEY_SCANNED_BOARDS = "ScannedBoards";
  private static final String KEY_REORDERED_BOARDS = "ReorderedBoards";
  private static final String KEY_CUT_PIECES = "CutPieces";
  private static final String KEY_GOOD_LENGTH = "GoodLength";
  private static final String KEY_BAD_LENGTH = "BadLength";
  private static final String KEY_PIECE_BUFFER = "PieceBuffer";
  private static final String KEY_FILTERED_PIECES = "FilteredPieces";
  private static final String KEY_REORDERED_PIECES = "ReorderedPieces";
  private static final String KEY_ASSEMBLED_PIECES = "AssembledPieces";
  private static final String KEY_PIECES = "Pieces";
  private static final String KEY_LAYERS = "Layers";
  private static final String KEY_COMPLETED_LAYERS = "CompletedLayers";
  private static final String KEY_COMPLETED_BEAMS = "CompletedBeams";
  private static final String KEY_LAST_COST = "LastCost";
  private static final String KEY_TOTAL_COST = "TotalCost";
  
  // quality values for board pieces
  private static final int QUALITY_GOOD = 1;
  private static final int QUALITY_BAD = 2;
  private static final int QUALITY_CURVED = 3;

  // user commands
  private static final String COMMAND_ASSEMBLE = "assemble";
  private static final String COMMAND_PIECE_OUT = "pout";
  private static final String COMMAND_PIECE_IN = "pin";
  private static final String COMMAND_PIECE_GO = "pgo";
  private static final String COMMAND_DROP = "discard";
  private static final String COMMAND_KEEP = "keep";
  private static final String COMMAND_CUT = "cut";
  private static final String COMMAND_BOARD_OUT = "bout";
  private static final String COMMAND_BOARD_IN = "bin";
  private static final String COMMAND_BOARD_GO = "bgo";
  private static final String COMMAND_SCAN = "scan";
  private static final String COMMAND_END = "end";
  private static final String COMMAND_POP = "pop";
  private static final String COMMAND_PUSH = "push";

  // execution responses
  private static final String RESPONSE_ERROR = "ERROR";
  private static final String RESPONSE_OKAY = "OKAY";

  // --------------------------------------------------------------------------
  //
  // types
  //
  // --------------------------------------------------------------------------

  private static record Interval (int from, int to) { }

  private static record BeamConfiguration(
    int beamLength,
    int numberOfLayers,
    int numberOfBeams,
    int beamSkipStart,
    int beamSkipEnd,
    int minLengthOfBoardInLayer,
    int gapToBoardAbutInConsecutiveLayers,
    int maxShiftCurvedCut,
    List<Interval> staticForbiddenZones) 
  { 
    public BeamConfiguration(JsonNode node)
    {
      this(
          getInt(node, KEY_BEAM_LENGTH),
          getInt(node, KEY_NUMBER_OF_LAYERS),
          getInt(node, KEY_NUMBER_OF_BEAMS),
          getInt(node, KEY_BEAM_SKIP_START),
          getInt(node, KEY_BEAM_SKIP_END),
          getInt(node, KEY_MIN_LENGTH_OF_BOARD_IN_LAYER),
          getInt(node, KEY_GAP_TO_BOARD_ABUT_IN_CONSECUTIVE_LAYERS),
          getInt(node, KEY_MAX_SHIFT_CURVED_CUT),
          getIntervals(node, KEY_STATIC_FORBIDDEN_ZONES)
          );
    }
  }

  private static record Part(
    String id,
    int quality,
    int startPosition,
    int endPosition) 
  { 
    public Part(JsonNode node)
    {
      this(
          getString(node, KEY_ID),
          getInt(node, KEY_QUALITY),
          (getInt(node, KEY_QUALITY) != QUALITY_CURVED ? getInt(node, KEY_START_POSITION) :
            getInt(node, KEY_START_POSITION)-beamConfiguration.maxShiftCurvedCut),
          (getInt(node, KEY_QUALITY) != QUALITY_CURVED ? getInt(node, KEY_END_POSITION) :
            getInt(node, KEY_END_POSITION)+beamConfiguration.maxShiftCurvedCut)
          );
      check (quality == QUALITY_GOOD || quality == QUALITY_BAD || quality == QUALITY_CURVED,
          "unknown quality value " + quality);
    }
    public String jsonString()
    {
      if (quality == QUALITY_CURVED)
        return "{" +
        stringString(KEY_ID, id) + "," +
        intString(KEY_QUALITY, quality) + "," +
        intString("MidPosition", startPosition+beamConfiguration.maxShiftCurvedCut) +
        "}";
      else
        return "{" +
        stringString(KEY_ID, id) + "," +
        intString(KEY_QUALITY, quality) + "," +
        intString(KEY_START_POSITION, startPosition) + "," +
        intString(KEY_END_POSITION, endPosition) +
        "}";  
    }
  };

  private static record Board(String id, int length, List<Part> parts) 
  { 
    public Board(JsonNode node) { 
      this(
          getString(node, KEY_ID),
          getInt(node, KEY_LENGTH),
          getParts(node, SCAN_BOARD_PARTS)
          ); 
    } 
    public String jsonString(String key)
    {
      return (key == null ? "" : "\"" + key + "\":") +
          "{" +
          stringString(KEY_ID, id) + "," +
          intString(KEY_LENGTH, length) + "," +
          arrayString(SCAN_BOARD_PARTS, parts, (Part part)->part.jsonString()) +
          "}";  
    }
  }
  
  private static record BoardList(List<Board> list) 
  { 
    public BoardList(JsonNode node) { this(getBoards(node)); }
  }
  
  private static record Boards(Deque<Board> deque) 
  { 
    public Boards() { this(new ArrayDeque<Board>()); }
    public Boards(Boards boards) { this(new ArrayDeque<Board>(boards.deque)); } 
    public String jsonString(String key)
    {
      return arrayString(key, deque, (Board board)->board.jsonString(null));
    }
  }
  
  private static record Piece(String id, int goodLength, int badLength) 
  { 
    public String jsonString(String key)
    {
      return (key == null ? "" : "\"" + key + "\":") +
          "{" + stringString(KEY_ID, id) + "," +
          intString(KEY_GOOD_LENGTH, goodLength) + "," +
          intString(KEY_BAD_LENGTH, badLength) + "}";
    }
  }
  
  private static record Pieces(Deque<Piece> deque) 
  { 
    public Pieces() { this(new ArrayDeque<Piece>()); }
    public Pieces(Pieces pieces) { this(new ArrayDeque<Piece>(pieces.deque)); }
    public String jsonString(String key)
    {
      return arrayString(key, deque, (Piece piece)->piece.jsonString(null));
    }
  }
  
  private static record Layer(String id, Pieces pieces)
  {
    // public Layer(String id) { this(id, new Pieces()); }
    // public Layer(Layer layer) { this(layer.id, new Pieces(layer.pieces)); }
    public String jsonString(String key)
    {
      return (key == null ? "" : "\"" + key + "\":") +
          "{" +
          stringString(KEY_ID, id) + "," +
          pieces.jsonString(KEY_PIECES) +
          "}";
    }
  }
  
  private static record Layers(List<Layer> list)
  {
    public Layers() { this(new ArrayList<Layer>()); }
    public Layers(Layers layers) { this(new ArrayList<Layer>(layers.list)); }    
    public String jsonString(String key)
    {
      return arrayString(key, list, (Layer layer)->layer.jsonString(null));
    }
  }
  
  private static record Beam(String id, Layers layers) 
  { 
    // public Beam(String id) { this(id, new Layers()); }
    // public Beam(Beam beam) { this(beam.id, new Layers(beam.layers)); }
    public String jsonString(String key) 
    { 
      return 
          (key == null ? "" : "\"" + key + "\":") +
          "{" +
          stringString(KEY_ID, id) + "," +
          layers.jsonString(KEY_LAYERS) +
          "}";
    }
  }
  
  private static record Beams(List<Beam> list) 
  { 
    public Beams() { this(new ArrayList<Beam>()); }
    public Beams(Beams beams) { this(new ArrayList<Beam>(beams.list)); }    
    public String jsonString(String key)
    {
      return arrayString(key, list, (Beam beam)->beam.jsonString(null));
    }
  }

  private static class MachineState
  {
    public int boardIndex = 0;
    public Boards scannedBoards = new Boards();
    public Optional<Board> boardBuffer = Optional.empty();
    public Boards reorderedBoards = new Boards();
    public Pieces cutPieces = new Pieces();
    public Pieces filteredPieces = new Pieces();
    public Optional<Piece> pieceBuffer = Optional.empty();
    public Pieces reorderedPieces = new Pieces();
    public Pieces assembledPieces = new Pieces();
    public Layers completedLayers = new Layers();
    public Beams completedBeams = new Beams();
    public int lastCost = 0;
    public int totalCost = 0;
    
    public MachineState() { }
    public MachineState(MachineState s)
    {
      boardIndex = s.boardIndex;
      scannedBoards = new Boards(s.scannedBoards);
      boardBuffer = s.boardBuffer;
      reorderedBoards = new Boards(s.reorderedBoards);
      cutPieces = new Pieces(s.cutPieces);
      filteredPieces = new Pieces(s.filteredPieces);
      pieceBuffer = s.pieceBuffer;
      reorderedPieces = new Pieces(s.reorderedPieces);
      assembledPieces = new Pieces(s.assembledPieces);
      completedLayers = new Layers(s.completedLayers);
      completedBeams = new Beams(s.completedBeams);
      lastCost = s.lastCost;
      totalCost = s.totalCost;
    }
    
    public String jsonString()
    {
      StringBuilder builder = new StringBuilder();
      builder.append("\"" + KEY_MACHINE_STATE + "\": {\n");
      builder.append("  " + intString(KEY_BOARD_INDEX, boardIndex) + ",\n");
      builder.append("  " + scannedBoards.jsonString(KEY_SCANNED_BOARDS) + ",\n");
      if (boardBuffer.isEmpty())
        builder.append("  " + stringString(KEY_BOARD_BUFFER, "") + ",\n");
      else
        builder.append("  " + boardBuffer.get().jsonString(KEY_BOARD_BUFFER) + ",\n");
      builder.append("  " + reorderedBoards.jsonString(KEY_REORDERED_BOARDS) + ",\n");
      builder.append("  " + cutPieces.jsonString(KEY_CUT_PIECES) + ",\n");
      if (pieceBuffer.isEmpty())
        builder.append("  " + stringString(KEY_PIECE_BUFFER, "") + ",\n");
      else
        builder.append("  " + pieceBuffer.get().jsonString(KEY_PIECE_BUFFER) + ",\n");
      builder.append("  " + filteredPieces.jsonString(KEY_FILTERED_PIECES) + ",\n");
      builder.append("  " + reorderedPieces.jsonString(KEY_REORDERED_PIECES) + ",\n");
      builder.append("  " + assembledPieces.jsonString(KEY_ASSEMBLED_PIECES) + ",\n");
      builder.append("  " + completedLayers.jsonString(KEY_COMPLETED_LAYERS) + ",\n");
      builder.append("  " + completedBeams.jsonString(KEY_COMPLETED_BEAMS) + ",\n");
      builder.append("  " + intString(KEY_LAST_COST, lastCost) + ",\n");
      builder.append("  " + intString(KEY_TOTAL_COST, totalCost) + "\n");
      builder.append("}");
      return builder.toString();
    }
  };

  // --------------------------------------------------------------------------
  //
  // global variables
  //
  // --------------------------------------------------------------------------

  // problem description 
  private static BeamConfiguration beamConfiguration;
  private static BoardList inputBoards;

  // the state on which we operate
  private static MachineState machineState;

  // the stack of states
  private static Deque<MachineState> stateStack = new ArrayDeque<MachineState>();

  // --------------------------------------------------------------------------
  //
  // initialization (JSON parsing)
  //
  // --------------------------------------------------------------------------

  private static void initialize(String path)
  {
    // https://mkyong.com/java/jackson-how-to-parse-json/
    // https://stackoverflow.com/questions/31870710/read-multiple-json-object-from-a-text-file
    try (FileInputStream input = new FileInputStream(path)) 
    {
      ObjectMapper mapper = new ObjectMapper();
      JsonNode node = mapper.readTree(input);
      beamConfiguration = new BeamConfiguration(get(node, KEY_BEAM_CONFIGURATION));
      inputBoards = new BoardList(get(node, KEY_INPUT_BOARDS));
      machineState = new MachineState();
    }
    catch (FileNotFoundException e) 
    {
      check(false, "file cannot be opened (" + e.getMessage() + ")");
    }
    catch (JsonProcessingException e) 
    {
      check(false, "file cannot be parsed (" + e.getMessage() + ")");
    }
    catch (IOException e) 
    {
      check(false, "file cannot be read (" + e.getMessage() + ")");
    }
  }

  private static JsonNode get(JsonNode node, String key)
  {
    JsonNode value = node.get(key);
    check(value != null, "there is no JSON key '" + key + "'");
    return value;
  }

  private static String getString(JsonNode node, String key)
  {
    JsonNode value = get(node, key);
    return value.asText();
  }
  
  private static int getInt(JsonNode node, String key)
  {
    JsonNode value = get(node, key);
    check (value.isInt(), "value " + value.asText() + " of key " + key + 
        " does not denote an integer");
    return value.asInt();
  }

  private static List<Interval> getIntervals(JsonNode node, String key)
  {
    List<Interval> list = new ArrayList<Interval>();
    JsonNode value = get(node, key);
    for (JsonNode elem : value)
    {
      int begin = getInt(elem, KEY_BEGIN);
      int end = getInt(elem, KEY_END);
      list.add(new Interval(begin, end));
    }
    return list;
  }

  private static List<Board> getBoards(JsonNode node)
  {
    List<Board> boards = new ArrayList<Board>();
    for (JsonNode elem : node)
    {
      Board board = new Board(get(elem, KEY_RAW_BOARD));
      boards.add(board);
    }
    return boards;
  }

  private static List<Part> getParts(JsonNode node, String key)
  {
    List<Part> parts = new ArrayList<Part>();
    JsonNode value = get(node, key);
    for (JsonNode elem : value)
    {
      Part part = new Part(elem);
      parts.add(part);
    }
    return parts;
  }

  // --------------------------------------------------------------------------
  //
  // printing
  //
  // --------------------------------------------------------------------------

  private static String intString(String key, int value)
  {
    return "\"" + key + "\":" + value;
  }
  
  private static String stringString(String key, String value)
  {
    return "\"" + key + "\":\"" + value + "\"";
  }
  
  private static <T> String arrayString(String key, Collection<T> values,
    Function<T,String> printer)
  {
    StringBuilder builder = new StringBuilder();
    if (key != null) builder.append("\"" + key + "\":");
    builder.append("[");
    Iterator<T> iterator = values.iterator();
    while (iterator.hasNext())
    {
      T value = iterator.next();
      builder.append(printer.apply(value));
      if (iterator.hasNext()) builder.append(",");
    }
    builder.append("]");
    return builder.toString();
  }
  
  // --------------------------------------------------------------------------
  //
  // execution
  //
  // --------------------------------------------------------------------------

  private static void execute()
  {
    try (BufferedReader reader = new BufferedReader(new InputStreamReader(System.in)))
    {
      while (true)
      {
        lastLine = reader.readLine();
        if (lastLine == null) return;
        machineState.lastCost = 0;
        execute(lastLine);
        machineState.totalCost += machineState.lastCost;
        System.out.println(RESPONSE_OKAY + "(" + lastLine + ")");
        System.out.println(machineState.jsonString());
        lastLine = null;
      }
    }
    catch (IOException e)
    {
      check(false, "cannot read input stream (" + e.getMessage() +")");
    }
  }
  
  private static void execute(String commandLine)
  {
    String[] args = commandLine.split(" ");
    int n = args.length;
    check (n != 0, "there is no command given");
    String command = args[0];
    switch (command)
    {
    case COMMAND_PUSH -> push();
    case COMMAND_POP -> pop();
    case COMMAND_END -> end();
    case COMMAND_SCAN -> scan();
    case COMMAND_BOARD_GO -> boardGo();
    case COMMAND_BOARD_IN -> boardIn();
    case COMMAND_BOARD_OUT -> boardOut();
    case COMMAND_CUT -> 
    {
      try
      {
        List<Integer> cuts = new ArrayList<Integer>();
        for (int i = 1; i < n; i++)
        {
          int cut = Integer.valueOf(args[i]);
          cuts.add(cut);
        }
        cut(cuts);
      }
      catch (NumberFormatException e)
      {
        check(false, "invalid cut position (" + e.getMessage() +")");
      }
    }
    case COMMAND_KEEP -> keep();
    case COMMAND_DROP -> drop();
    case COMMAND_PIECE_GO -> pieceGo();
    case COMMAND_PIECE_IN -> pieceIn();
    case COMMAND_PIECE_OUT -> pieceOut();
    case COMMAND_ASSEMBLE -> assemble();
    default -> check(false, "invalid command (" + command + ")");
    }
  }

  // pushing to and popping from the stack
  private static void push()
  {
    stateStack.push(machineState);
    machineState = new MachineState(machineState);
  }
  private static void pop()
  {
    check(!stateStack.isEmpty(), "context stack is empty");
    machineState = stateStack.pop();
  }

  // ending the execution
  private static void end()
  {
    int number = machineState.completedBeams.list.size();
    int number0 = beamConfiguration.numberOfBeams;
    check(number == number0, 
        number + " beams have been completed but " +
        number0 + " beams have been requested");
  }

  // providing the next board
  private static void scan()
  {
    check(machineState.boardIndex < inputBoards.list.size(), "there is no input board");
    Board board = inputBoards.list.get(machineState.boardIndex);
    machineState.boardIndex++;
    machineState.scannedBoards.deque.addLast(board);
  }

  // the machine actions
  private static void boardGo()
  {
    check(!machineState.scannedBoards.deque.isEmpty(), "there is no scanned board");
    Board board = machineState.scannedBoards.deque.removeFirst();
    machineState.reorderedBoards.deque.addLast(board);
  }
  private static void boardOut()
  {
    check(!machineState.scannedBoards.deque.isEmpty(), "there is no scanned board"); 
    Board board = machineState.scannedBoards.deque.removeFirst();
    if (machineState.boardBuffer.isPresent())
    {
      Board board0 = machineState.boardBuffer.get();
      machineState.reorderedBoards.deque.addLast(board0);
    }
    machineState.boardBuffer = Optional.of(board);
  }
  private static void boardIn()
  {
    check(machineState.scannedBoards.deque.isEmpty(), "there are still scanned boards"); 
    check(machineState.boardBuffer.isPresent(), " there is no board in the buffer");
    Board board0 = machineState.boardBuffer.get();
    machineState.reorderedBoards.deque.addLast(board0);
    machineState.boardBuffer = Optional.empty();
  }
  private static void cut(List<Integer> cuts)
  {
    check(!machineState.reorderedBoards.deque.isEmpty(), "there is no reorderd board"); 
    Board board = machineState.reorderedBoards.deque.removeFirst();

    // cuts are within beam range and strictly ordered
    int min = Math.max(1, beamConfiguration.beamSkipStart);
    int max = board.length-Math.min(1, beamConfiguration.beamSkipEnd);
    for (Integer cut : cuts)
    {
      check(cut >= min, "cut " + cut + " must be at least " + min);
      min = cut+1;
    }
    if (!cuts.isEmpty())
    {
      int cut = cuts.getLast();
      check (cut <= max, "cut " + cut + " must be at most " + max);
    }

    // every curved part has a cut
    for(Part part : board.parts)
    {
      if (part.quality != QUALITY_CURVED) continue;
      boolean hasCut = cuts.stream().anyMatch(
          (Integer cut)-> part.startPosition <= cut && cut <= part.endPosition);
      check(hasCut, "there is no cut for curved part " + part.id + 
          " in board " + board.id);
    }
   
    // handle margins of boards as bad parts
    Deque<Part> parts = new ArrayDeque<Part>();
    if (beamConfiguration.beamSkipStart != 0)
    {
      Part part = new Part("-1", QUALITY_BAD, 
          0, beamConfiguration.beamSkipStart);
      parts.addFirst(part);
    }
    int start0 = beamConfiguration.beamSkipStart;
    int end0 = board.length-beamConfiguration.beamSkipEnd;
    for (Part part : board.parts)
    {
      int start = Math.max(part.startPosition, start0);
      int end = Math.min(part.endPosition, end0);
      if (start >= end) continue;
      parts.add(new Part(part.id, part.quality, start, end));
    }
    if (beamConfiguration.beamSkipEnd != 0)
    {
      Part part = new Part(String.valueOf(board.parts.size()), QUALITY_BAD, 
          board.length-beamConfiguration.beamSkipEnd, board.length);
      parts.addLast(part);
    }
    
    // construct the resulting pieces
    int index = 0;
    int pos = 0;
    while (pos < board.length)
    {
      int cut = index < cuts.size() ? cuts.get(index) : board.length;
      int goodLength = 0;
      int badLength = 0;
      for (Part part: parts)
      {
        int pstart = part.startPosition;
        int pend = part.endPosition;
        if (pend < pos || pstart > cut) continue;
        int cstart = Math.max(pstart, pos);
        int cend = Math.min(pend, cut);
        int clen = cend-cstart;
        if (part.quality == QUALITY_BAD)
          badLength += clen;
        else
          goodLength += clen;
      }
      Piece piece = new Piece(board.id + "_" + index, goodLength, badLength);
      machineState.cutPieces.deque.addLast(piece);
      index++;
      pos = cut;
    }

  }
  private static void keep()
  {
    check(!machineState.cutPieces.deque.isEmpty(), "there are no cut pieces");
    Piece piece = machineState.cutPieces.deque.removeFirst();
    check(piece.badLength == 0, "bad piece " + piece.id + " passes the filter");
    check(piece.goodLength >= beamConfiguration.minLengthOfBoardInLayer,
        "too short piece " + piece.id + " of length " + piece.goodLength +
        "passes the filter");
    machineState.filteredPieces.deque.addLast(piece);
  }
  private static void drop()
  {
    check(!machineState.cutPieces.deque.isEmpty(), "there are no cut pieces");
    Piece piece = machineState.cutPieces.deque.removeFirst();
    machineState.lastCost = piece.goodLength;
  }
  private static void pieceGo()
  {
    check(!machineState.filteredPieces.deque.isEmpty(), "there is no filtered piece");
    Piece piece = machineState.filteredPieces.deque.removeFirst();
    machineState.reorderedPieces.deque.addLast(piece);
  }
  private static void pieceOut()
  {
    check(!machineState.filteredPieces.deque.isEmpty(), "there is no filtered piece"); 
    Piece piece = machineState.filteredPieces.deque.removeFirst();
    if (machineState.pieceBuffer.isPresent())
    {
      Piece piece0 = machineState.pieceBuffer.get();
      machineState.reorderedPieces.deque.addLast(piece0);
    }
    machineState.pieceBuffer = Optional.of(piece);
  }
  private static void pieceIn()
  {
    check(machineState.filteredPieces.deque.isEmpty(), "there are still filtered pieces");
    check(machineState.pieceBuffer.isPresent(), "there is no piece in the buffer");
    Piece piece = machineState.pieceBuffer.get();
    machineState.reorderedPieces.deque.addLast(piece);
    machineState.pieceBuffer = Optional.empty();
  }
  private static void assemble()
  {
    check(!machineState.reorderedPieces.deque.isEmpty(), "there is no reordered piece"); 
    Piece piece = machineState.reorderedPieces.deque.removeFirst();
    check(piece.badLength == 0, "bad piece " + piece.id + " is assembled to beam");
    check(piece.goodLength >= beamConfiguration.minLengthOfBoardInLayer,
        "too short piece " + piece.id + " of length " + piece.goodLength +
        "is assembled to beam");
    int blen = piece.goodLength; 
    for (Piece piece0 : machineState.assembledPieces.deque)
      blen += piece0.goodLength;
    check(blen <= beamConfiguration.beamLength, "assembling piece " + piece.id + 
        " leads to a too long layer of length " + blen);
    int blen_ = blen;
    boolean forbidden = beamConfiguration.staticForbiddenZones.stream().anyMatch(
        (Interval interval)-> interval.from < blen_ && blen_ < interval.to);
    check(!forbidden, "assembling piece " + piece.id +
        " leads to end position " + blen + 
        " which is in a forbidden zone");
    Layers layers = machineState.completedLayers;
    int nlayers = layers.list.size();
    if (nlayers >= 1)
    {
      Layer layer0 = layers.list.get(nlayers-1);
      int blen0 = 0;
      for (Piece piece0 : layer0.pieces.deque)
      {
        blen0 += piece0.goodLength;
        if (blen0 == beamConfiguration.beamLength) break;
        int diff = Math.abs(blen-blen0);
        check(diff >= beamConfiguration.gapToBoardAbutInConsecutiveLayers,
            "assembling piece " + piece.id + 
            " leads to end position " + blen + 
            " which has too little distance " + diff + 
            " to piece " + piece0.id + " in previous layer" +
            " with end position " + blen0);
      }
    }
    machineState.assembledPieces.deque.add(piece);
    if (blen == beamConfiguration.beamLength)
    {
      String beamId = String.valueOf(machineState.completedBeams.list.size());
      String layerId = String.valueOf(machineState.completedLayers.list.size());
      Layer layer = new Layer(beamId + "_" + layerId, machineState.assembledPieces);
      machineState.completedLayers.list.add(layer);
      machineState.assembledPieces = new Pieces();
      if (nlayers+1 == beamConfiguration.numberOfLayers())
      {
        Beam beam = new Beam (beamId, machineState.completedLayers);
        machineState.completedBeams.list.add(beam);
        machineState.completedLayers = new Layers();
      }
    }
  }
}
// ----------------------------------------------------------------------------
// end of file
// ----------------------------------------------------------------------------
