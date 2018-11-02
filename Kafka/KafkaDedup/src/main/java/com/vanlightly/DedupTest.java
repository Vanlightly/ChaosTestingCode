package com.vanlightly;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import org.apache.kafka.clients.producer.Callback;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.Producer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;

class Tracking {
	public int AckCount;
	public List<String> PosAckedMessages;
	public List<String> NegAckedMessages;
	
	public Tracking() {
		AckCount  = 0;
		PosAckedMessages = new ArrayList<String>();
		NegAckedMessages = new ArrayList<String>();
	}
}

class MyCallback implements Callback {
	private final String messageValue;
	private final Tracking tracking;

	public MyCallback(String messageValue, Tracking tracking) {
		this.messageValue = messageValue;
		this.tracking = tracking;
	}

	@Override
	public void onCompletion(RecordMetadata metaData, Exception exception) {
		this.tracking.AckCount++;
  		if (exception != null) {
  			this.tracking.NegAckedMessages.add(this.messageValue);
  			System.out.println(exception.getMessage());
    	}
    	else {
    		this.tracking.PosAckedMessages.add(this.messageValue);
    	}
    }
}

public class DedupTest {
	
	private static Tracking tracking;

	public static void main(String[] args) {
		String topic = args[0];
		int count = Integer.parseInt(args[1]);
		String bootstrapServers = args[2];
		String posAckedFile = args[3];
		String negAckedFile = args[4];
		String enableIdempotence = args[5];
		
		sendMessages(topic, count, bootstrapServers, enableIdempotence, posAckedFile, negAckedFile);
	}
	
	private static void sendMessages(String topic, int count, String bootstrapServers, String enableIdempotence, String posAckFile, String negAckFile) {
		
		tracking = new Tracking();
		
		Properties props = new Properties();
		props.put("bootstrap.servers", bootstrapServers);
		props.put("group.id", "dedup.test");

		if(enableIdempotence.equals("true")) {
			props.put("enable.idempotence", true);
			System.out.println("IDEMPOTENT PRODUCER");
		}
		else {
			props.put("enable.idempotence", false);
			System.out.println("NON IDEMPOTENT PRODUCER");
		}

		props.put("request.timeout.ms", 240000);
		props.put("retries", Integer.MAX_VALUE);
		props.put("max.in.flight.requests.per.connection", 5);
		props.put("client.id", "dedup.tester");
		props.put("acks", "all");
		//props.put("reconnect.backoff.ms", 1000);
		//props.put("retry.backoff.ms", 1000);
		props.put("linger.ms", 1000);
		props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
		props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
		
		int sendCount = 0;
		Producer<String, String> producer = new KafkaProducer<String, String>(props);
		while(sendCount < count) {
		      
		      if(sendCount - tracking.AckCount > 10000) {
		    	  Wait(100);
		    	  //System.out.println("Reached in flight limit, waiting...");
		      }
		      else {
		    	  String record = String.format("%s", sendCount);
			      		    	  
			      producer.send(new ProducerRecord<>(topic, record, record), new MyCallback(record, tracking));
			      
			      sendCount++;
			      
			      if (sendCount % 50000 == 0) {
			    	  System.out.println(sendCount);
			      }
		      }
		}
		
		producer.close();
		
		try {
		
			writeToFile(tracking.PosAckedMessages, posAckFile);
			writeToFile(tracking.NegAckedMessages, negAckFile);
		}
		catch(IOException e) {
			System.out.println(e);
		}
		
		System.out.println("FINISHED");
	}
	
	private static void writeToFile(List<String> lines, String fileName) throws IOException {
		FileWriter writer = new FileWriter(fileName); 
		for(String str: lines) {
			writer.write(str);
			writer.write(System.lineSeparator());
		}
		writer.close();
	}
	
	private static void Wait(int milliseconds) {
		try {
			Thread.sleep(milliseconds);
		}
		catch(InterruptedException e)
		{}
	}
}